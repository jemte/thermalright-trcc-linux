"""Pydantic request/response models and shared helpers for all API endpoints."""
from __future__ import annotations

from fastapi import HTTPException
from pydantic import BaseModel

# ── Shared helpers ────────────────────────────────────────────────────

_NON_SERIALIZABLE_KEYS = frozenset({"image", "colors"})


def dispatch_result(result: dict) -> dict:
    """Convert dispatcher result dict to JSON-safe API response. Raises 400 on failure."""
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
    return {k: v for k, v in result.items() if k not in _NON_SERIALIZABLE_KEYS}

# ── Device models ──────────────────────────────────────────────────────

class DeviceResponse(BaseModel):
    id: int
    name: str
    vid: int
    pid: int
    protocol: str
    resolution: tuple[int, int]
    path: str


class ThemeResponse(BaseModel):
    name: str
    category: str
    is_animated: bool
    has_config: bool
    preview_url: str = ""


class WebThemeResponse(BaseModel):
    id: str
    category: str
    preview_url: str
    has_video: bool = False


class MaskResponse(BaseModel):
    name: str
    preview_url: str


# ── Display request models ─────────────────────────────────────────────

class ColorRequest(BaseModel):
    hex: str


class BrightnessRequest(BaseModel):
    level: int


class RotationRequest(BaseModel):
    degrees: int


class SplitRequest(BaseModel):
    mode: int


# ── LED request models ─────────────────────────────────────────────────

class LEDColorRequest(BaseModel):
    hex: str


class LEDModeRequest(BaseModel):
    mode: str


class LEDBrightnessRequest(BaseModel):
    level: int


class LEDSensorRequest(BaseModel):
    source: str


class ZoneColorRequest(BaseModel):
    hex: str


class ZoneModeRequest(BaseModel):
    mode: str


class ZoneBrightnessRequest(BaseModel):
    level: int


class ZoneToggleRequest(BaseModel):
    on: bool


class ZoneSyncRequest(BaseModel):
    enabled: bool
    interval: int | None = None


class SegmentToggleRequest(BaseModel):
    on: bool


class ClockFormatRequest(BaseModel):
    is_24h: bool


class TempUnitRequest(BaseModel):
    unit: str


# ── Theme request models ───────────────────────────────────────────────

class ThemeLoadRequest(BaseModel):
    name: str
    resolution: str | None = None


class ThemeSaveRequest(BaseModel):
    name: str
