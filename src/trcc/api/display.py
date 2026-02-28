"""LCD display control endpoints — brightness, rotation, color, mask, overlay."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, UploadFile

from trcc.api.models import (
    BrightnessRequest,
    ColorRequest,
    RotationRequest,
    SplitRequest,
    dispatch_result,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/display", tags=["display"])


def _get_display():
    """Get the active DisplayDispatcher, raise 409 if not connected."""
    from trcc.api import _display_dispatcher

    if not _display_dispatcher or not _display_dispatcher.connected:
        raise HTTPException(status_code=409, detail="No LCD device selected. POST /devices/{id}/select first.")
    return _display_dispatcher


def _parse_hex(hex_color: str) -> tuple[int, int, int]:
    """Parse hex color string to (r, g, b). Raises 400 on invalid format."""
    from trcc.core.models import parse_hex_color

    rgb = parse_hex_color(hex_color)
    if rgb is None:
        raise HTTPException(status_code=400, detail="Invalid hex color (use 6-digit hex, e.g. 'ff0000')")
    return rgb



@router.post("/color")
def set_color(body: ColorRequest) -> dict:
    """Send solid color to LCD."""
    lcd = _get_display()
    r, g, b = _parse_hex(body.hex)
    return dispatch_result(lcd.send_color(r, g, b))


@router.post("/brightness")
def set_brightness(body: BrightnessRequest) -> dict:
    """Set display brightness (1=25%, 2=50%, 3=100%). Persists to config."""
    lcd = _get_display()
    return dispatch_result(lcd.set_brightness(body.level))


@router.post("/rotation")
def set_rotation(body: RotationRequest) -> dict:
    """Set display rotation (0, 90, 180, 270). Persists to config."""
    lcd = _get_display()
    return dispatch_result(lcd.set_rotation(body.degrees))


@router.post("/split")
def set_split(body: SplitRequest) -> dict:
    """Set split mode (0=off, 1-3=Dynamic Island). Persists to config."""
    lcd = _get_display()
    return dispatch_result(lcd.set_split_mode(body.mode))


@router.post("/reset")
def reset_display() -> dict:
    """Reset device by sending solid red frame."""
    lcd = _get_display()
    return dispatch_result(lcd.reset())


@router.post("/mask")
async def load_mask(image: UploadFile) -> dict:
    """Upload and apply mask overlay (PNG)."""
    import tempfile
    from pathlib import Path

    lcd = _get_display()

    data = await image.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Mask image exceeds 10 MB limit")

    # Write to temp file for dispatcher (expects path)
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        result = lcd.load_mask(tmp_path)
        return dispatch_result(result)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/overlay")
async def render_overlay(dc_path: str, send: bool = True) -> dict:
    """Render overlay from DC config path and optionally send to device."""
    lcd = _get_display()
    result = lcd.render_overlay(dc_path, send=send)
    return dispatch_result(result)


@router.get("/status")
def display_status() -> dict:
    """Get current display state — resolution, device path, connection."""
    from trcc.api import _display_dispatcher

    if not _display_dispatcher or not _display_dispatcher.connected:
        return {"connected": False}

    lcd = _display_dispatcher
    return {
        "connected": True,
        "resolution": lcd.resolution,
        "device_path": lcd.device_path,
    }
