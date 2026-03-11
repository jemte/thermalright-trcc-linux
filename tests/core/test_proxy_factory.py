"""Tests for ipc.py proxy factory functions."""

from trcc.core.instance import InstanceKind
from trcc.ipc import (
    APIDisplayProxy,
    APILEDProxy,
    IPCDisplayProxy,
    IPCLEDProxy,
    create_lcd_proxy,
    create_led_proxy,
)


class TestCreateLcdProxy:
    """create_lcd_proxy() returns correct proxy type for InstanceKind."""

    def test_gui_returns_ipc_proxy(self):
        proxy = create_lcd_proxy(InstanceKind.GUI)
        assert isinstance(proxy, IPCDisplayProxy)

    def test_api_returns_api_proxy(self):
        proxy = create_lcd_proxy(InstanceKind.API)
        assert isinstance(proxy, APIDisplayProxy)


class TestCreateLedProxy:
    """create_led_proxy() returns correct proxy type for InstanceKind."""

    def test_gui_returns_ipc_proxy(self):
        proxy = create_led_proxy(InstanceKind.GUI)
        assert isinstance(proxy, IPCLEDProxy)

    def test_api_returns_api_proxy(self):
        proxy = create_led_proxy(InstanceKind.API)
        assert isinstance(proxy, APILEDProxy)
