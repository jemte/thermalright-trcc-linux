"""OS/platform initialization command dataclasses.

These commands cross the OS boundary — the handler decides which platform
adapter executes them. Callers (CLI, API, GUI) are completely blind to the
underlying OS.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..command_bus import OSCommand


@dataclass(frozen=True)
class InitPlatformCommand(OSCommand):
    """Bootstrap the platform: logging, OS detection, settings.

    Dispatched once at startup by every composition root (CLI, API, GUI).
    """
    verbosity: int = 0


@dataclass(frozen=True)
class DiscoverDevicesCommand(OSCommand):
    """Scan for all connected TRCC devices, classify, connect, and wire buses.

    OS → scan() → classify by VID:PID/protocol → connect → _wire_bus()
    sets lcd_bus or led_bus.  After dispatch, check app.has_lcd / app.has_led.

    Optional path: restrict to a specific device path (e.g. '/dev/sg2').
    """
    path: str | None = None
