#!/usr/bin/env python3
"""Allow running as: python -m trcc

Sets up crash logging BEFORE any imports — ensures every OS gets
a log file at ~/.trcc/trcc.log even if the app crashes on startup.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path

# Early logging — catches import failures, DI errors, platform issues.
# Must run before any trcc imports. All 4 OS's get a log file.
_log_dir = Path.home() / '.trcc'
_log_dir.mkdir(parents=True, exist_ok=True)
_log_path = _log_dir / 'trcc.log'

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.handlers.RotatingFileHandler(
            _log_path, maxBytes=1_000_000, backupCount=3),
    ],
)
log = logging.getLogger('trcc.main')
log.info("Starting TRCC — platform=%s, executable=%s", sys.platform, sys.executable)

try:
    # Auto-launch GUI when invoked as trcc-gui.exe (windowed PyInstaller build)
    if os.path.basename(sys.executable).lower().startswith('trcc-gui'):
        from trcc.cli import gui
        sys.exit(gui() or 0)
    else:
        from trcc.cli import main
        sys.exit(main())
except Exception:
    log.critical("Fatal startup error", exc_info=True)
    raise
