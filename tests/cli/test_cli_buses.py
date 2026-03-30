"""Verify CLI wrapper functions dispatch through CommandBus.

Fixtures reflect the real DI chain:
  TrccApp.init() → os_bus.dispatch(DiscoverDevicesCommand) → lcd_bus/led_bus wired
  → CLI dispatches lcd_bus/led_bus commands → device method called

Strategy:
  - Use the conftest mock_app (already set as TrccApp._instance).
  - Wire a real CommandBus to a mock device so assertions reach the device method.
  - Patch _connect_or_fail to return 0 (simulates successful os_bus connect).
  - Call the CLI function and assert the device method was invoked.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from trcc.core.app import TrccApp

# ── LCD fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture()
def mock_lcd():
    lcd = MagicMock()
    lcd.send_image.return_value = {"success": True, "message": "sent"}
    lcd.send_color.return_value = {"success": True, "message": "color set"}
    lcd.set_brightness.return_value = {"success": True, "message": "brightness 50%"}
    lcd.set_rotation.return_value = {"success": True, "message": "rotated"}
    lcd.set_split_mode.return_value = {"success": True, "message": "split off"}
    return lcd


@pytest.fixture()
def wired_lcd(mock_lcd):
    """Wire mock_lcd into TrccApp._instance with a real CommandBus."""
    mock_app = TrccApp._instance
    mock_app.lcd_device = mock_lcd
    mock_app.lcd_bus = TrccApp.build_lcd_bus(mock_app, mock_lcd)  # type: ignore[arg-type]
    return mock_lcd


# ── LED fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture()
def mock_led():
    led = MagicMock()
    led.set_color.return_value = {"success": True, "message": "color ok"}
    led.set_brightness.return_value = {"success": True, "message": "bright ok"}
    led.set_sensor_source.return_value = {"success": True, "message": "source ok"}
    led.set_zone_color.return_value = {"success": True, "message": "zone ok"}
    return led


@pytest.fixture()
def wired_led(mock_led):
    """Wire mock_led into TrccApp._instance with a real CommandBus."""
    mock_app = TrccApp._instance
    mock_app.led_device = mock_led
    mock_app.led_bus = TrccApp.build_led_bus(mock_app, mock_led)  # type: ignore[arg-type]
    return mock_led


# ── LCD CLI commands ──────────────────────────────────────────────────────────


class TestDisplayCLIBus:
    def test_send_image_calls_device(self, wired_lcd, tmp_path):
        from trcc.cli._display import send_image

        img = tmp_path / "x.png"
        img.touch()
        with patch("trcc.cli._display._connect_or_fail", return_value=0):
            send_image(MagicMock(), str(img))
        wired_lcd.send_image.assert_called_once_with(str(img))

    def test_send_color_calls_device(self, wired_lcd):
        from trcc.cli._display import send_color

        with patch("trcc.cli._display._connect_or_fail", return_value=0):
            send_color(MagicMock(), "ff0000")
        wired_lcd.send_color.assert_called_once_with(255, 0, 0)

    def test_set_brightness_calls_device(self, wired_lcd):
        from trcc.cli._display import set_brightness

        with patch("trcc.cli._display._connect_or_fail", return_value=0):
            set_brightness(MagicMock(), 2)
        wired_lcd.set_brightness.assert_called_once_with(2)

    def test_set_brightness_failure_prints_hint(self, wired_lcd, capsys):
        from trcc.cli._display import set_brightness

        wired_lcd.set_brightness.return_value = {
            "success": False,
            "error": "Brightness: 1-3 (level) or 0-100 (percent)",
        }
        with patch("trcc.cli._display._connect_or_fail", return_value=0):
            rc = set_brightness(MagicMock(), 99)
        out = capsys.readouterr().out
        assert rc == 1
        assert "1 = 25%" in out

    def test_set_rotation_calls_device(self, wired_lcd):
        from trcc.cli._display import set_rotation

        with patch("trcc.cli._display._connect_or_fail", return_value=0):
            set_rotation(MagicMock(), 90)
        wired_lcd.set_rotation.assert_called_once_with(90)

    def test_set_split_mode_calls_device(self, wired_lcd):
        from trcc.cli._display import set_split_mode

        with patch("trcc.cli._display._connect_or_fail", return_value=0):
            set_split_mode(MagicMock(), 1)
        wired_lcd.set_split_mode.assert_called_once_with(1)


# ── LED CLI commands ──────────────────────────────────────────────────────────


class TestLedCLIBus:
    def test_set_color_calls_device(self, wired_led):
        from trcc.cli._led import set_color

        with patch("trcc.cli._led._connect_or_fail", return_value=0):
            set_color(MagicMock(), "00ff00")
        wired_led.set_color.assert_called_once_with(0, 255, 0)

    def test_set_led_brightness_calls_device(self, wired_led):
        from trcc.cli._led import set_led_brightness

        with patch("trcc.cli._led._connect_or_fail", return_value=0):
            set_led_brightness(MagicMock(), 75)
        wired_led.set_brightness.assert_called_once_with(75)

    def test_set_sensor_source_calls_device(self, wired_led):
        from trcc.cli._led import set_sensor_source

        with patch("trcc.cli._led._connect_or_fail", return_value=0):
            set_sensor_source(MagicMock(), "gpu")
        wired_led.set_sensor_source.assert_called_once_with("gpu")

    def test_set_zone_color_calls_device(self, wired_led):
        from trcc.cli._led import set_zone_color

        with patch("trcc.cli._led._connect_or_fail", return_value=0):
            set_zone_color(MagicMock(), 2, "0000ff")
        wired_led.set_zone_color.assert_called_once_with(2, 0, 0, 255)
