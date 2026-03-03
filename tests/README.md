# TRCC Linux — Test Suite

## Overview

4646 tests across 54 test files covering all 5 protocols (SCSI, HID, LED, Bulk, LY), services, adapters, CLI, API, GUI components, and integration.

## Running Tests

```bash
# Full suite (recommended)
PYTHONPATH=src pytest tests/ -x -q

# With coverage
PYTHONPATH=src pytest tests/ --cov=trcc --cov-report=term-missing

# Single file
PYTHONPATH=src pytest tests/test_models.py -x -q

# Linting + type checking (run before committing)
ruff check .
python -m pyright
```

## Test Files

```
tests/
├── hid_testing/
│   ├── test_device_factory.py       # Device protocol factory + routing
│   ├── test_device_hid.py           # HID Type 2/3 LCD protocol
│   ├── test_device_led.py           # LED HID segment display protocol
│   └── test_led_controller.py       # LED controller + effects
├── test_ansi_preview.py             # Terminal ANSI art preview
├── test_api.py                      # FastAPI REST adapter
├── test_api_ext.py                  # Extended API tests
├── test_architecture.py             # Hexagonal architecture constraints
├── test_ax120_display.py            # AX120 LED segment display
├── test_base_panel.py               # BasePanel lifecycle + state
├── test_cli.py                      # Typer CLI commands
├── test_cli_device.py               # CLI device commands
├── test_cli_display.py              # CLI display commands
├── test_cli_led.py                  # CLI LED commands
├── test_cli_system.py               # CLI system commands
├── test_cli_theme.py                # CLI theme commands
├── test_cloud_video.py              # Cloud video playback
├── test_conf.py                     # Settings/config persistence
├── test_controllers.py              # MVC controllers
├── test_data_repository.py          # XDG paths, on-demand download
├── test_dc_config_class.py          # DcConfig dataclass
├── test_dc_parser.py                # config1.dc overlay parsing
├── test_dc_writer.py                # config1.dc writing
├── test_debug_report.py             # Diagnostic report tool
├── test_debug_report_ext.py         # Extended diagnostic tests
├── test_device_bulk.py              # Bulk USB protocol
├── test_device_detector.py          # USB device scan + registries
├── test_device_implementations.py   # Per-device protocol variants
├── test_device_lcd.py               # SCSI RGB565 frame send
├── test_device_led_kvm.py           # KVM LED backend
├── test_device_ly.py                # LY bulk protocol
├── test_device_scsi.py              # Low-level SCSI commands
├── test_doctor.py                   # Dependency health check + setup wizard
├── test_doctor_ext.py               # Extended doctor tests
├── test_frame_device.py             # Frame device ABC + transport
├── test_hardware_info.py            # Hardware info collection
├── test_hr10_display.py             # HR10 LED segment display
├── test_integration.py              # Cross-component integration
├── test_led_segment.py              # LED segment display renderer
├── test_media_player.py             # FFmpeg video frame extraction
├── test_memory.py                   # Memory/state management
├── test_models.py                   # Domain constants, resolution pipeline
├── test_overlay_renderer.py         # PIL-based overlay rendering
├── test_qt_base.py                  # BasePanel, BaseThemeBrowser
├── test_qt_constants.py             # Layout coords, sizes, colors
├── test_qt_device_preview.py        # Device preview widget
├── test_qt_led_gui.py               # LED GUI panel
├── test_qt_main_window.py           # Main window integration
├── test_qt_misc_widgets.py          # Misc PySide6 widgets
├── test_qt_theme_gui.py             # Theme browser GUI
├── test_qt_widgets.py               # PySide6 widget tests
├── test_services.py                 # All service classes
├── test_system_config.py            # Dashboard config persistence
├── test_system_info.py              # CPU/GPU/RAM/disk sensor collection
├── test_system_sensors.py           # Hardware sensor discovery
├── test_theme_cloud.py              # Cloud theme HTTP fetch
├── test_theme_downloader.py         # Theme pack download manager
└── test_theme_service.py            # Theme service logic
```

## Principles

- **Isolation**: Each test is independent — no shared mutable state
- **Mocking**: Hardware access (USB, SCSI, HID) is fully mocked
- **Coverage**: 76%+ line coverage
- **Fast**: Full suite runs in ~60 seconds
- **CI-safe**: Tests work as root (CI) and regular user (dev)
