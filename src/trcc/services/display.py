"""Display pipeline orchestrator — coordinates theme, overlay, media -> LCD frame.

Pure Python, no Qt dependencies.
Controllers (PySide6, Typer CLI, FastAPI) are thin wrappers that call this
service and fire callbacks.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable, Tuple

import trcc.conf as _conf

from ..core.models import SPLIT_MODE_RESOLUTIONS, SPLIT_OVERLAY_MAP
from ..core.paths import RESOURCES_DIR
from .device import DeviceService
from .image import ImageService
from .media import MediaService
from .overlay import OverlayService
from .theme_loader import ThemeLoader
from .theme_persistence import ThemePersistence

log = logging.getLogger(__name__)


class DisplayService:
    """Display pipeline: theme -> overlay -> brightness/rotation -> LCD frame.

    Orchestrates sub-services (DeviceService, OverlayService, MediaService).
    Sub-services are injected, not owned. Theme loading and persistence
    delegated to ThemeLoader and ThemePersistence (SRP).
    """

    def __init__(
        self,
        devices: DeviceService,
        overlay: OverlayService,
        media: MediaService,
        ensure_data_fn: Any = None,
        theme_svc: Any = None,
        cpu_percent_fn: Callable[[], float] | None = None,
    ) -> None:
        # Sub-services (injected)
        self.devices = devices
        self.overlay = overlay
        self.media = media
        self._cpu_percent_fn = cpu_percent_fn
        self._ensure_data_fn = ensure_data_fn

        # Theme loader (injected with same sub-services)
        self._loader = ThemeLoader(overlay, media, theme_svc=theme_svc)
        self._persistence = ThemePersistence(theme_svc=theme_svc)

        # Working directory (Windows GifDirectory pattern)
        self.working_dir = Path(tempfile.mkdtemp(prefix="trcc_work_"))

        # State
        self.current_image: Any | None = None  # Native surface (QImage)
        self._clean_background: Any | None = None  # Original bg before overlay
        self.current_theme_path: Path | None = None
        self.auto_send = True
        self.rotation = 0  # directionB: 0, 90, 180, 270
        self.brightness = 100  # percent (0-100), config restores actual value
        self.split_mode = 0  # 0-3=Dynamic Island style
        self._split_overlay_cache: dict[tuple[int, int], Any] = {}  # (style,rot)->surface

        # Pre-baked video frame cache (None when inactive)
        self._cache: Any | None = None  # VideoFrameCache

        # Render cache for render_overlay() — avoids redundant compositing + encoding
        # on repeated sends when nothing has changed (static image keepalive, metrics
        # tick with no overlay change, etc.).  Tuple of (background_id, overlay_version,
        # brightness, rotation, split_mode) → rendered image.
        # Set to None whenever any input changes; repopulated on next render_overlay().
        self._render_cache: tuple[Any, ...] | None = None  # key
        self._render_cache_image: Any | None = None  # cached result

        # Callback: fired when background data extraction finishes
        self.on_data_ready: Any | None = None

        # Theme directories
        self._local_dir: Path | None = None
        self._web_dir: Path | None = None
        self._masks_dir: Path | None = None
        self._mask_source_dir: Path | None = None

        # Per-instance resolution — independent of the global settings singleton.
        # Initialised to the singleton value on first use; overwritten by
        # set_resolution() so two simultaneous LCD devices each own their own
        # dimensions without trampling each other via the singleton.
        self._width: int = 0
        self._height: int = 0

    # -- Properties --------------------------------------------------------

    @property
    def lcd_width(self) -> int:
        """Return LCD width. Must be initialized via initialize() or set_resolution()."""
        return self._width

    @property
    def lcd_height(self) -> int:
        """Return LCD height. Must be initialized via initialize() or set_resolution()."""
        return self._height

    @property
    def lcd_size(self) -> tuple[int, int]:
        """Return LCD (width, height). Both must be non-zero after initialization."""
        return (self._width, self._height)

    # -- Initialization ----------------------------------------------------

    def initialize(self, data_dir: Path, width: int = 0, height: int = 0) -> None:
        """Initialize service with data directory and device resolution.

        Args:
            data_dir: Data directory for theme/overlay content
            width: Device LCD width (required for proper operation)
            height: Device LCD height (required for proper operation)

        Width/height must be provided from device handshake. This instance owns
        its resolution independent of the settings singleton (multi-device support).
        """
        log.debug("DisplayService: init data_dir=%s w=%d h=%d", data_dir, width, height)
        self._data_dir = data_dir

        # Require explicit resolution - no fallback to singleton
        if width and height:
            self._width = width
            self._height = height
        else:
            # If called without resolution, log warning but don't crash
            # This can happen in test scenarios
            log.warning(
                "DisplayService.initialize called without resolution; "
                "device resolution not available yet"
            )
            return

        self.media.set_target_size(self.lcd_width, self.lcd_height)
        self.overlay.set_resolution(self.lcd_width, self.lcd_height)

        if self.lcd_width and self.lcd_height:
            self._setup_dirs(self.lcd_width, self.lcd_height)

    def _setup_dirs(self, width: int, height: int) -> None:
        """Locate and set theme/web/mask directories from current disk state.

        Data download is handled by EnsureDataCommand (dispatched by
        SetResolutionCommand on the LCD bus). This method only reads
        what is already on disk — no downloading, no background threads.
        """
        if self._ensure_data_fn is not None:
            import threading

            fn = self._ensure_data_fn

            def _bg():
                fn(width, height)
                _conf.settings._resolve_paths()
                if self.on_data_ready is not None:
                    self.on_data_ready()

            threading.Thread(target=_bg, daemon=True, name="data-extract").start()
        _conf.settings._resolve_paths()

        td = _conf.settings.theme_dir
        self._local_dir = td.path if td and td.exists() else None
        self._web_dir = (
            _conf.settings.web_dir
            if _conf.settings.web_dir and _conf.settings.web_dir.exists()
            else None
        )
        self._masks_dir = _conf.settings.masks_dir

    def cleanup(self) -> None:
        """Clean up working directory on exit."""
        if self.working_dir and self.working_dir.exists():
            shutil.rmtree(self.working_dir, ignore_errors=True)

    # -- Resolution --------------------------------------------------------

    def set_resolution(self, width: int, height: int, persist: bool = True) -> None:
        """Set LCD resolution for this device instance and update sub-services.

        Also updates the global settings singleton so that path resolution
        (theme_dir, web_dir, masks_dir) and persistence work correctly for
        this device.  Each DisplayService instance owns its own _width/_height
        so simultaneous devices do not overwrite each other's dimensions.
        """
        if width == self._width and height == self._height:
            return
        log.info("Resolution changed: %dx%d -> %dx%d", self._width, self._height, width, height)
        self._width = width
        self._height = height
        _conf.settings.set_resolution(width, height, persist=persist)
        self.media.set_target_size(width, height)
        self.overlay.set_resolution(width, height)

        if width and height:
            self._setup_dirs(width, height)

    # -- Display adjustments -----------------------------------------------

    def set_rotation(self, degrees: int) -> Any | None:
        """Set display rotation. Returns rendered image or None."""
        self.rotation = degrees % 360
        self.invalidate_render_cache()
        if self._cache and self._cache.active:
            self._cache.rebuild_from_rotation(self.rotation)
        return self._render_and_process()

    def set_brightness(self, percent: int) -> Any | None:
        """Set display brightness. Returns rendered image or None."""
        self.brightness = max(0, min(100, percent))
        self.invalidate_render_cache()
        if self._cache and self._cache.active:
            self._cache.rebuild_from_brightness(self.brightness)
        return self._render_and_process()

    def set_split_mode(self, mode: int) -> Any | None:
        """Set split mode (C# myLddVal: 0=off, 1-3=Dynamic Island style).

        Only affects 1600x720 widescreen devices. Returns rendered image.
        """
        self.split_mode = mode if mode in (0, 1, 2, 3) else 0
        self.invalidate_render_cache()
        return self._render_and_process()

    @property
    def is_widescreen_split(self) -> bool:
        """True if current resolution supports split mode."""
        return self.lcd_size in SPLIT_MODE_RESOLUTIONS

    # -- Frame conversion --------------------------------------------------

    def _convert_media_frames(self) -> None:
        """Convert decoded frames to native renderer surfaces.

        RawFrame (from VideoDecoder/ThemeZtDecoder) → native surface via renderer.
        Converts in-place once at load time.
        """
        from ..core.ports import RawFrame

        frames = self.media._frames
        if not frames:
            return
        r = ImageService._r()
        first = frames[0]
        if isinstance(first, RawFrame):
            self.media._frames = [r.from_raw_rgb24(f) for f in frames]
        else:
            # Already native surfaces (QImage) — use as-is
            self.media._frames = list(frames)

    # -- Theme loading (delegates to ThemeLoader) --------------------------

    def load_local_theme(self, theme) -> dict:
        """Load a local theme with DC config, mask, and overlay."""
        if self._cache is not None:  # Invalidate previous video cache
            self._cache.shutdown()
        self._cache = None
        result = self._loader.load_local_theme(theme, self.lcd_size, self.working_dir)

        # Convert decoded frames to native renderer surfaces (if animated)
        if result.get("is_animated"):
            self._convert_media_frames()

        # Wire up state from loader result
        self._mask_source_dir = result.get("mask_source_dir")
        self.current_theme_path = result.get("theme_path")
        log.debug("load_local_theme: _mask_source_dir=%s", self._mask_source_dir)

        # Set current_image from result or from video first frame
        if result.get("image"):
            self.current_image = result["image"]
            self._clean_background = result["image"]
        elif result.get("is_animated"):
            first_frame = self.media.get_frame(0)
            if first_frame:
                self.current_image = first_frame
                self._clean_background = first_frame

        # New background — discard any stale render cache
        self.invalidate_render_cache()

        # Build pre-baked cache for animated themes (only if device is connected)
        if result.get("is_animated") and self.media.has_frames and self.devices.selected:
            self._build_video_cache()

        # Render with adjustments if we have a static image
        if result.get("image") and not result.get("is_animated"):
            result["image"] = self._render_and_process()

        return result

    def load_cloud_theme(self, theme) -> dict:
        """Load a cloud video theme as background."""
        if self._cache is not None:  # Invalidate previous video cache
            self._cache.shutdown()
        self._cache = None
        result = self._loader.load_cloud_theme(theme, self.working_dir)
        log.debug("load_cloud_theme: loader result keys=%s", list(result.keys()))

        # Wire up state — cloud themes are video-only, so preserve
        # existing mask source dir (user may have applied a mask before
        # selecting the cloud video background)
        if result.get("mask_source_dir") is not None:
            self._mask_source_dir = result["mask_source_dir"]
        self.current_theme_path = result.get("theme_path")

        # Convert decoded frames to native renderer surfaces
        self._convert_media_frames()
        log.debug(
            "load_cloud_theme: frames converted, count=%d",
            len(self.media._frames) if self.media._frames else 0,
        )

        first_frame = self.media.get_frame(0)
        log.debug(
            "load_cloud_theme: first_frame=%s", type(first_frame).__name__ if first_frame else None
        )
        if first_frame:
            self.current_image = first_frame
            self._clean_background = first_frame
        # New background — discard any stale render cache
        self.invalidate_render_cache()
        result["image"] = self.current_image

        # Build pre-baked cache for cloud video themes
        if self.media.has_frames:
            log.debug("load_cloud_theme: building video cache")
            self._build_video_cache()
            log.debug(
                "load_cloud_theme: cache active=%s", self._cache.active if self._cache else False
            )
        return result

    def apply_mask(self, mask_dir: Path) -> Any | None:
        """Apply a mask overlay on top of current content."""
        # Restore clean background so old mask isn't baked in
        if self._clean_background is not None:
            self.current_image = self._clean_background
        elif not self.current_image:
            self.current_image = ImageService.solid_color(0, 0, 0, *self.lcd_size)

        self._mask_source_dir = self._loader.apply_mask(mask_dir, self.working_dir, self.lcd_size)
        log.debug("apply_mask: _mask_source_dir=%s", self._mask_source_dir)

        # Mask change invalidates both video cache and render cache
        if self._cache is not None:
            self._cache.shutdown()
        self._cache = None
        self.invalidate_render_cache()
        if self.media.has_frames:
            self._build_video_cache()

        return self.render_overlay()

    # -- Image loading (kept on DisplayService -- tied to state) -----------

    def load_image_file(self, path: Path) -> Any | None:
        """Load a static image file. Returns rendered image or None."""
        self._load_static_image(path)
        return self._render_and_process()

    def set_clean_background(self, image: Any) -> None:
        """Set both current_image and clean_background to a native surface.

        Used when loading a custom background image (C# imagePicture + bitmapBGK).
        """
        self._clean_background = image
        self.current_image = image
        self.invalidate_render_cache()

    def _load_static_image(self, path: Path) -> None:
        """Load and resize a static image to LCD dimensions."""
        try:
            self.current_image = ImageService.open_and_resize(path, *self.lcd_size)
            self._clean_background = self.current_image
            self.invalidate_render_cache()
        except Exception as e:
            log.error("Failed to load image: %s", e)

    def _create_black_background(self) -> None:
        """Create black background for mask-only themes."""
        self.current_image = ImageService.solid_color(0, 0, 0, *self.lcd_size)
        self.invalidate_render_cache()

    # -- Rendering ---------------------------------------------------------

    def _render_and_process(self) -> Any | None:
        """Render overlay on current image, apply brightness + rotation."""
        if not self.current_image:
            log.debug("_render_and_process: no current_image")
            return None
        image = self.current_image
        log.debug(
            "_render_and_process: current_image type=%s overlay_enabled=%s",
            type(image).__name__,
            self.overlay.enabled,
        )
        if self.overlay.enabled:
            image = self.overlay.render(image)
            log.debug("_render_and_process: after overlay type=%s", type(image).__name__)
        return self._apply_adjustments(image)

    def _render_cache_key(self, bg: Any) -> tuple[Any, ...]:
        """Build a cache key from all inputs that affect render_overlay() output.

        Uses ``overlay.prospective_cache_version`` — the key the overlay *would*
        produce on the next render given current stored metrics — rather than
        ``overlay.cache_version`` (the key from the last completed render).
        This ensures the display-level cache is invalidated as soon as metrics
        change, even before the overlay layer has been re-rendered, preventing
        stale cache hits that cause visual freezes on the physical display.
        """
        return (
            id(bg),
            self.overlay.prospective_cache_version,
            self.brightness,
            self.rotation,
            self.split_mode,
        )

    def invalidate_render_cache(self) -> None:
        """Discard the render cache. Call whenever rendering inputs change."""
        self._render_cache = None
        self._render_cache_image = None

    def render_overlay(self) -> Any | None:
        """Force-render overlay (for live editing). Returns image or None.

        Caches the last rendered result keyed on (background identity,
        overlay config version, brightness, rotation, split_mode).  Repeated
        calls with no changes — e.g. keepalive, metrics ticks where the
        overlay text has not changed — return the same object, making the
        encode cache in DeviceService effective and avoiding redundant work.
        """
        # Use clean background (no old overlay baked in)
        bg = self._clean_background or self.current_image
        if not bg:
            log.debug("render_overlay: no background, creating black bg")
            self._create_black_background()
            bg = self.current_image
        if not bg:
            return None

        key = self._render_cache_key(bg)
        if key == self._render_cache and self._render_cache_image is not None:
            log.debug("render_overlay: cache hit")
            return self._render_cache_image

        image = self.overlay.render(bg, force=True)
        result = self._apply_adjustments(image)
        self._render_cache = key
        self._render_cache_image = result
        return result

    def _apply_adjustments(self, image: Any) -> Any:
        """Apply brightness, rotation, and split overlay to image.

        For non-square displays at 90/270, rotation swaps dimensions
        (640x480 -> 480x640). The preview shows this portrait image.
        The resize-back to native dims happens at encoding time in
        encode_for_device() — matching C# which also shows a portrait
        preview but sends landscape data.
        """
        if self.brightness >= 100 and self.rotation == 0 and not self.split_mode:
            return image
        image = ImageService.apply_brightness(image, self.brightness)
        image = ImageService.apply_rotation(image, self.rotation)
        return self._apply_split_overlay(image)

    def _apply_split_overlay(self, image: Any) -> Any:
        """Composite Dynamic Island overlay for widescreen split mode."""
        if not self.split_mode or not self.is_widescreen_split:
            return image

        key = (self.split_mode, self.rotation)
        asset_name = SPLIT_OVERLAY_MAP.get(key)
        if not asset_name:
            return image

        overlay = self._split_overlay_cache.get(key)
        if overlay is None:
            overlay = self._load_split_overlay(asset_name)
            self._split_overlay_cache[key] = overlay

        if overlay is None:
            return image

        try:
            r = ImageService._r()
            image = r.convert_to_rgba(image)
            img_w, img_h = r.surface_size(image)
            ovl_w, ovl_h = r.surface_size(overlay)
            if (ovl_w, ovl_h) != (img_w, img_h):
                overlay = r.resize(overlay, img_w, img_h)
            image = r.composite(image, overlay, (0, 0))
            return r.convert_to_rgb(image)
        except Exception as e:
            log.error("Split overlay composite failed: %s", e)
            return image

    @staticmethod
    def _load_split_overlay(asset_name: str) -> Any | None:
        """Load a split overlay PNG from assets/gui/ as native surface."""
        try:
            path = os.path.join(RESOURCES_DIR, asset_name)
            if os.path.exists(path):
                r = ImageService._r()
                img = r.open_image(path)
                return r.convert_to_rgba(img)
            log.warning("Split overlay not found: %s", path)
        except Exception as e:
            log.error("Failed to load split overlay %s: %s", asset_name, e)
        return None

    def set_video_fit_mode(self, mode: str) -> Any | None:
        """Set video fit mode. Re-decodes frames. Returns preview image."""
        if self.media.set_fit_mode(mode):
            self._convert_media_frames()
            frame = self.media.get_frame()
            if frame:
                self.current_image = frame
                return self._render_and_process()
        return self._render_and_process()

    # -- Video playback ----------------------------------------------------

    def video_tick(self) -> dict | None:
        """Advance one video frame. Returns dict or None if not playing."""
        frame, should_send, progress = self.media.tick()
        if not frame:
            return None

        self.current_image = frame

        # Fast path: pre-baked cache active — use directly
        if self._cache and self._cache.active:
            cf = self.media.state.current_frame
            total = self.media.state.total_frames
            index = (cf - 1) % total if total > 0 else 0
            preview, encoded = self._cache.get_frame(index)
            return {
                "preview": preview,
                "frame_index": index,
                "progress": progress,
                "send_image": None,
                "encoded": encoded,
            }

        # Fallback: original pipeline (overlay disabled, or cache not built)
        if self.overlay.enabled:
            frame = self.overlay.render(frame)

        processed = self._apply_adjustments(frame)

        result = {
            "preview": processed,
            "progress": progress,
            "send_image": processed if (should_send and self.auto_send) else None,
        }

        return result

    def get_video_interval(self) -> int:
        """Get video frame interval in ms for timer setup."""
        return self.media.frame_interval_ms

    def is_video_playing(self) -> bool:
        """Check if video is currently playing."""
        return self.media.is_playing

    # -- Video frame cache -------------------------------------------------

    def _build_video_cache(self) -> None:
        """Build pre-baked video frame cache from current state."""
        from .video_cache import VideoFrameCache

        device = self.devices.selected
        if not device:
            raise RuntimeError("Cannot build video cache — no device selected")
        protocol, resolution, fbl, use_jpeg = device.encoding_params
        cache = VideoFrameCache()
        cache.build(
            frames=self.media._frames,
            mask=(
                self.overlay.theme_mask
                if self.overlay.enabled and self.overlay.theme_mask_visible
                else None
            ),
            mask_position=self.overlay.theme_mask_position,
            overlay_svc=self.overlay if self.overlay.enabled else None,
            metrics=self.overlay._metrics,
            brightness=self.brightness,
            rotation=self.rotation,
            protocol=protocol,
            resolution=resolution,
            fbl=fbl,
            use_jpeg=use_jpeg,
            device_info=device,
        )
        self._cache = cache
        if self._cpu_percent_fn is not None:
            log.info(
                "video cache built: %d frames, trcc CPU %.1f%%",
                len(self.media._frames),
                self._cpu_percent_fn(),
            )
        else:
            log.info("video cache built: %d frames", len(self.media._frames))

    def rebuild_video_cache_metrics(self, metrics: Any) -> None:
        """Rebuild video cache with new metrics text."""
        if self._cache and self._cache.active:
            self._cache.rebuild_from_metrics(
                self.overlay if self.overlay.enabled else None, metrics
            )

    # -- Blocking video loop (CLI / API) ------------------------------------

    def run_video_loop(
        self,
        video_path: Path,
        *,
        overlay_config: dict | None = None,
        mask_path: Path | None = None,
        metrics_fn: Any | None = None,
        on_frame: Any | None = None,
        on_progress: Any | None = None,
        loop: bool = True,
        duration: float = 0,
    ) -> dict:
        """Unified video+overlay pipeline for CLI and API adapters.

        Loads video, sets up overlay (config + mask + metrics polling),
        runs the tick loop, and calls ``on_frame`` per processed frame.

        Args:
            video_path: Video/GIF/ZT file to play.
            overlay_config: Overlay element config dict (from
                ``build_overlay_config()``). Enables overlay if provided.
            mask_path: Mask PNG file or directory. Auto-resized to LCD dims.
            metrics_fn: Callable returning ``HardwareMetrics`` — polled once
                per second for live overlay updates.
            on_frame: Callback ``(processed_image)`` — adapter sends to device.
            on_progress: Callback ``(percent, current_time, total_time)``.
            loop: Whether to loop the video.
            duration: Stop after N seconds (0 = no limit).

        Returns:
            Result dict with success/error/message.
        """
        log.info(
            "run_video_loop: path=%s overlay=%s mask=%s loop=%s duration=%s",
            video_path,
            bool(overlay_config),
            bool(mask_path),
            loop,
            duration,
        )

        # 1. Load video
        w, h = self.lcd_size
        self.media.set_target_size(w, h)
        if not self.media.load(video_path):
            log.error("run_video_loop: failed to load %s", video_path)
            return {"success": False, "error": f"Failed to load: {video_path}"}

        self._convert_media_frames()

        total = self.media.state.total_frames
        fps = self.media.state.fps
        log.info("run_video_loop: loaded %d frames, %.0ffps, %dx%d", total, fps, w, h)

        # 2. Set up overlay if config or mask provided
        if overlay_config or mask_path:
            if overlay_config:
                log.debug("run_video_loop: overlay config with %d elements", len(overlay_config))
                self.overlay.set_config(overlay_config)
            if mask_path:
                mask_img = OverlayService.load_mask_from_path(
                    Path(mask_path), self.overlay._renderer, w, h
                )
                if mask_img is not None:
                    log.debug("run_video_loop: mask loaded from %s", mask_path)
                    self.overlay.set_theme_mask(mask_img)
            self.overlay.enabled = True

        # 3. Start playback + run tick loop
        self.media._state.loop = loop
        self.media.play()
        return self._run_tick_loop(
            metrics_fn=metrics_fn, on_frame=on_frame, on_progress=on_progress, duration=duration
        )

    def _run_tick_loop(
        self,
        *,
        metrics_fn: Any | None = None,
        on_frame: Any | None = None,
        on_progress: Any | None = None,
        duration: float = 0,
    ) -> dict:
        """Blocking tick loop — shared by run_video_loop and theme-load.

        Assumes media is already loaded + playing, overlay already configured.
        Polls metrics, composites overlay, applies adjustments, calls callbacks.

        Returns:
            Result dict with success/message.
        """
        import time as _time

        total = self.media.state.total_frames
        fps = self.media.state.fps
        interval = self.media.frame_interval_ms / 1000.0
        start = _time.monotonic()
        last_metrics = 0.0

        try:
            while self.media.is_playing:
                frame, should_send, progress = self.media.tick()
                if frame is None:
                    break

                # Poll metrics once per second
                if metrics_fn and self.overlay.enabled:
                    now = _time.monotonic()
                    if now - last_metrics >= 1.0:
                        self.overlay.update_metrics(metrics_fn())
                        last_metrics = now

                # Composite overlay
                if self.overlay.enabled:
                    frame = self.overlay.render(frame)

                # Apply brightness/rotation
                processed = self._apply_adjustments(frame)

                # Send to device
                if on_frame and should_send:
                    on_frame(processed)

                # Progress callback
                if on_progress and progress:
                    on_progress(*progress)

                # Duration limit
                if duration and (_time.monotonic() - start) >= duration:
                    break

                _time.sleep(interval)

        except KeyboardInterrupt:
            return {"success": True, "message": "Stopped", "frames": total, "fps": fps}

        return {"success": True, "message": "Done", "frames": total, "fps": fps}

    # -- LCD send ----------------------------------------------------------

    def send_current_image(self) -> bytes | None:
        """Prepare current image for LCD send. Returns encoded bytes or None."""
        if not self.current_image:
            return None
        image = self.current_image
        if self.overlay.enabled:
            image = self.overlay.render(image)
        image = self._apply_adjustments(image)
        return self._encode_for_device(image)

    def _encode_for_device(self, img: Any) -> bytes:
        """Encode image for LCD device."""
        device = self.devices.selected
        if not device:
            raise RuntimeError("Cannot encode for device — no device selected")
        protocol, resolution, fbl, use_jpeg = device.encoding_params
        return ImageService.encode_for_device(
            img, protocol, resolution, fbl, use_jpeg, device_info=device
        )

    # -- Theme save (delegates to ThemePersistence) ------------------------

    def save_theme(self, name: str, data_dir: Path) -> Tuple[bool, str]:
        """Save current config as a custom theme.

        Custom themes always go to user_content_dir (~/.trcc-user/) so they
        survive uninstall and data re-downloads.
        """
        data_dir = _conf.settings.user_content_dir
        ok, msg = ThemePersistence.save(
            name,
            data_dir,
            self.lcd_size,
            current_image=self._clean_background or self.current_image,
            overlay=self.overlay,
            mask_source_dir=self._mask_source_dir,
            media_source_path=self.media.source_path,
            media_is_playing=self.media.is_playing,
            current_theme_path=self.current_theme_path,
        )
        if ok:
            safe_name = f"Custom_{name}" if not name.startswith("Custom_") else name
            self.current_theme_path = (
                data_dir / f"theme{self.lcd_width}{self.lcd_height}" / safe_name
            )
        return ok, msg

    def export_config(self, export_path: Path) -> Tuple[bool, str]:
        """Export current theme as .tr or JSON file."""
        return self._persistence.export_config(
            export_path,
            self.current_theme_path,
            self.lcd_width,
            self.lcd_height,
        )

    def import_config(self, import_path: Path, data_dir: Path) -> Tuple[bool, str]:
        """Import theme from .tr or JSON file."""
        # Fall back to user-writable dir on system-wide installs (#51)
        if not os.access(data_dir, os.W_OK):
            data_dir = _conf.settings.user_data_dir
        ok, result = self._persistence.import_config(import_path, data_dir, self.lcd_size)
        if ok and not isinstance(result, str):
            self.load_local_theme(result)
            return True, f"Imported: {import_path.stem}"
        return ok, result if isinstance(result, str) else "Import failed"

    # -- Directory properties ----------------------------------------------

    @property
    def local_dir(self) -> Path | None:
        return self._local_dir

    @property
    def web_dir(self) -> Path | None:
        return self._web_dir

    @property
    def masks_dir(self) -> Path | None:
        return self._masks_dir
