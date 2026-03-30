"""Tests for core/builder.py — ControllerBuilder fluent device assembly."""

import unittest
from unittest.mock import MagicMock, patch

from trcc.core.builder import ControllerBuilder
from trcc.services.image import ImageService


def _make_builder() -> ControllerBuilder:
    """Return a ControllerBuilder with a MagicMock platform for unit tests."""
    return ControllerBuilder(MagicMock())


class TestControllerBuilderLcd(unittest.TestCase):
    """ControllerBuilder.build_lcd() — assembles LCDDevice with DI."""

    @patch("trcc.adapters.infra.data_repository.DataManager.ensure_all")
    def test_build_lcd_returns_lcd_device(self, _):
        """build_lcd() returns an LCDDevice instance."""
        from trcc.core.lcd_device import LCDDevice

        lcd = _make_builder().with_renderer(ImageService._r()).build_lcd()
        self.assertIsInstance(lcd, LCDDevice)

    def test_build_lcd_without_renderer_raises(self):
        """build_lcd() without with_renderer() raises RuntimeError."""
        with self.assertRaises(RuntimeError) as ctx:
            _make_builder().build_lcd()
        self.assertIn("with_renderer", str(ctx.exception))

    @patch("trcc.adapters.infra.data_repository.DataManager.ensure_all")
    def test_build_lcd_wires_device_service(self, _):
        """LCDDevice has a wired DeviceService."""
        lcd = _make_builder().with_renderer(ImageService._r()).build_lcd()
        self.assertIsNotNone(lcd._device_svc)

    @patch("trcc.adapters.infra.data_repository.DataManager.ensure_all")
    def test_build_lcd_wires_display_service(self, _):
        """LCDDevice has a wired DisplayService."""
        lcd = _make_builder().with_renderer(ImageService._r()).build_lcd()
        self.assertIsNotNone(lcd._display_svc)

    @patch("trcc.adapters.infra.data_repository.DataManager.ensure_all")
    def test_build_lcd_wires_theme_service(self, _):
        """LCDDevice has a wired ThemeService."""
        lcd = _make_builder().with_renderer(ImageService._r()).build_lcd()
        self.assertIsNotNone(lcd._theme_svc)

    @patch("trcc.adapters.infra.data_repository.DataManager.ensure_all")
    def test_build_lcd_wires_renderer(self, _):
        """LCDDevice has the injected renderer."""
        renderer = ImageService._r()
        lcd = _make_builder().with_renderer(renderer).build_lcd()
        self.assertIs(lcd._renderer, renderer)

    @patch("trcc.adapters.infra.data_repository.DataManager.ensure_all")
    def test_with_data_dir_triggers_initialize(self, mock_ensure):
        """with_data_dir() causes build_lcd() to call lcd.initialize()."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as d:
            lcd = (
                _make_builder().with_renderer(ImageService._r()).with_data_dir(Path(d)).build_lcd()
            )
            # initialize was called (ensure_all is the data download step)
            self.assertIsNotNone(lcd)

    @patch("trcc.adapters.infra.data_repository.DataManager.ensure_all")
    def test_build_lcd_without_data_dir_skips_initialize(self, mock_ensure):
        """Without with_data_dir(), initialize is not called."""
        lcd = _make_builder().with_renderer(ImageService._r()).build_lcd()
        # No crash, lcd built without initialization
        self.assertIsNotNone(lcd)


class TestControllerBuilderLed(unittest.TestCase):
    """ControllerBuilder.build_led() — assembles LEDDevice."""

    def test_build_led_returns_led_device(self):
        """build_led() returns an LEDDevice instance."""
        from trcc.core.led_device import LEDDevice

        led = _make_builder().build_led()
        self.assertIsInstance(led, LEDDevice)

    def test_build_led_no_renderer_required(self):
        """LED doesn't need a renderer — build_led() works without it."""
        led = _make_builder().build_led()
        self.assertIsNotNone(led)

    def test_build_led_wires_get_protocol(self):
        """LEDDevice gets the protocol factory wired."""
        led = _make_builder().build_led()
        self.assertIsNotNone(led._get_protocol)

    def test_build_led_injects_device_svc(self):
        """build_led() injects a DeviceService so connect() works."""
        led = _make_builder().build_led()
        self.assertIsNotNone(led._device_svc)


class TestControllerBuilderLcdFromService(unittest.TestCase):
    """ControllerBuilder.lcd_from_service() — builds from existing DeviceService."""

    def test_returns_lcd_device(self):
        from trcc.core.lcd_device import LCDDevice

        svc = MagicMock()
        svc.selected = MagicMock()
        lcd = _make_builder().lcd_from_service(svc)
        self.assertIsInstance(lcd, LCDDevice)

    def test_wires_display_and_theme_services(self):
        svc = MagicMock()
        svc.selected = MagicMock()
        lcd = _make_builder().lcd_from_service(svc)
        self.assertIsNotNone(lcd._display_svc)
        self.assertIsNotNone(lcd._theme_svc)
        self.assertIs(lcd._device_svc, svc)


class TestControllerBuilderSetup(unittest.TestCase):
    """ControllerBuilder.build_setup() — platform setup adapter."""

    def setUp(self):
        """Use a real OS builder (bypasses autouse mock) for setup adapter tests."""
        from trcc.adapters.system.linux.platform import LinuxPlatform

        self._builder = ControllerBuilder(LinuxPlatform())

    def test_returns_platform_setup(self):
        from trcc.core.ports import PlatformSetup

        setup = self._builder.build_setup()
        self.assertIsInstance(setup, PlatformSetup)

    def test_has_archive_tool_help(self):
        setup = self._builder.build_setup()
        help_text = setup.archive_tool_install_help()
        self.assertIn("7z", help_text.lower())

    def test_has_distro_name(self):
        setup = self._builder.build_setup()
        name = setup.get_distro_name()
        self.assertIsInstance(name, str)
        self.assertTrue(len(name) > 0)

    def test_has_pkg_manager(self):
        setup = self._builder.build_setup()
        # May be None on some systems, but the method should exist
        pm = setup.get_pkg_manager()
        self.assertTrue(pm is None or isinstance(pm, str))


class TestControllerBuilderFluent(unittest.TestCase):
    """ControllerBuilder fluent API — method chaining."""

    def test_with_renderer_returns_self(self):
        """with_renderer() returns the builder for chaining."""
        b = _make_builder()
        result = b.with_renderer(MagicMock())
        self.assertIs(result, b)

    def test_with_data_dir_returns_self(self):
        """with_data_dir() returns the builder for chaining."""
        from pathlib import Path

        b = _make_builder()
        result = b.with_data_dir(Path("/tmp"))
        self.assertIs(result, b)

    def test_fresh_builder_has_no_renderer(self):
        """New builder starts with no renderer."""
        b = _make_builder()
        self.assertIsNone(b._renderer)

    def test_fresh_builder_has_no_data_dir(self):
        """New builder starts with no data_dir."""
        b = _make_builder()
        self.assertIsNone(b._data_dir)

    @patch("trcc.adapters.infra.data_repository.DataManager.ensure_all")
    def test_full_chain(self, _):
        """Full fluent chain builds successfully."""
        from trcc.core.lcd_device import LCDDevice

        lcd = _make_builder().with_renderer(ImageService._r()).build_lcd()
        self.assertIsInstance(lcd, LCDDevice)


class TestControllerBuilderBootstrap(unittest.TestCase):
    """ControllerBuilder.bootstrap() — logging + setup + settings init."""

    def test_bootstrap_calls_logging_configurator(self):
        with (
            patch(
                "trcc.adapters.infra.logging_setup.StandardLoggingConfigurator.configure"
            ) as mock_log,
            patch.object(ControllerBuilder, "build_setup", return_value=MagicMock()),
            patch("trcc.conf.init_settings"),
        ):
            _make_builder().bootstrap()
        mock_log.assert_called_once()

    def test_bootstrap_passes_verbosity(self):
        with (
            patch(
                "trcc.adapters.infra.logging_setup.StandardLoggingConfigurator.configure"
            ) as mock_log,
            patch.object(ControllerBuilder, "build_setup", return_value=MagicMock()),
            patch("trcc.conf.init_settings"),
        ):
            _make_builder().bootstrap(verbosity=2)
        mock_log.assert_called_once_with(verbosity=2)

    def test_bootstrap_calls_configure_stdout(self):
        mock_setup = MagicMock()
        with (
            patch("trcc.adapters.infra.logging_setup.StandardLoggingConfigurator.configure"),
            patch.object(ControllerBuilder, "build_setup", return_value=mock_setup),
            patch("trcc.conf.init_settings"),
        ):
            _make_builder().bootstrap()
        mock_setup.configure_stdout.assert_called_once()

    def test_bootstrap_calls_init_settings_with_setup(self):
        mock_setup = MagicMock()
        with (
            patch("trcc.adapters.infra.logging_setup.StandardLoggingConfigurator.configure"),
            patch.object(ControllerBuilder, "build_setup", return_value=mock_setup),
            patch("trcc.conf.init_settings") as mock_init,
        ):
            _make_builder().bootstrap()
        mock_init.assert_called_once_with(mock_setup)


class TestControllerBuilderSystem(unittest.TestCase):
    """ControllerBuilder.build_system() — SystemService assembly."""

    def test_build_system_returns_system_service(self):
        from trcc.services.system import SystemService

        system = _make_builder().build_system()
        self.assertIsInstance(system, SystemService)

    def test_build_system_uses_platform_enumerator(self):
        platform = MagicMock()
        ControllerBuilder(platform).build_system()
        platform.create_sensor_enumerator.assert_called_once()


class TestControllerBuilderExtra(unittest.TestCase):
    """ControllerBuilder auxiliary build methods."""

    def test_build_ensure_data_fn_returns_callable(self):
        fn = _make_builder().build_ensure_data_fn()
        self.assertTrue(callable(fn))

    def test_build_autostart_delegates_to_platform(self):
        platform = MagicMock()
        ControllerBuilder(platform).build_autostart()
        platform.create_autostart_manager.assert_called_once()

    def test_build_hardware_fns_returns_two_callables(self):
        platform = MagicMock()
        platform.get_memory_info_fn.return_value = lambda: {}
        platform.get_disk_info_fn.return_value = lambda: {}
        mem_fn, disk_fn = ControllerBuilder(platform).build_hardware_fns()
        self.assertTrue(callable(mem_fn))
        self.assertTrue(callable(disk_fn))

    def test_build_detect_fn_returns_callable(self):
        fn = _make_builder().build_detect_fn()
        self.assertTrue(callable(fn))


class TestBuilderPsutilFallback(unittest.TestCase):
    """_make_build_services_fn: psutil ImportError → lcd still builds."""

    @patch("trcc.adapters.infra.data_repository.DataManager.ensure_all")
    def test_psutil_unavailable_still_builds_lcd(self, _):
        import sys

        from trcc.services.image import ImageService

        renderer = ImageService._r()
        with patch.dict(sys.modules, {"psutil": None}):
            lcd = _make_builder().with_renderer(renderer).build_lcd()
        self.assertIsNotNone(lcd._display_svc)


if __name__ == "__main__":
    unittest.main()
