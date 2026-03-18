"""Re-export stub — moved to adapters/detection/facade_windows.py."""
from trcc.adapters.detection.facade_windows import *  # noqa: F401,F403
from trcc.adapters.detection.facade_windows import (  # noqa: F401 — private names
    _find_physical_drive,
    _match_device,
    _parse_vid_pid,
)
