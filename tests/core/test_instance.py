"""Tests for core/instance.py — instance detection."""

import unittest
from unittest.mock import patch

from trcc.core.instance import InstanceKind, find_active


class TestInstanceKind(unittest.TestCase):
    """InstanceKind enum values."""

    def test_gui_value(self):
        assert InstanceKind.GUI.value == "gui"

    def test_api_value(self):
        assert InstanceKind.API.value == "api"


class TestFindActive(unittest.TestCase):
    """find_active() — detects running trcc instances."""

    @patch("trcc.core.instance._gui_running", return_value=True)
    def test_returns_gui_when_socket_available(self, _mock):
        assert find_active() == InstanceKind.GUI

    @patch("trcc.core.instance._gui_running", return_value=False)
    @patch("trcc.core.instance._api_running", return_value=True)
    def test_returns_api_when_server_responds(self, _api, _gui):
        assert find_active() == InstanceKind.API

    @patch("trcc.core.instance._gui_running", return_value=False)
    @patch("trcc.core.instance._api_running", return_value=False)
    def test_returns_none_when_nothing_running(self, _api, _gui):
        assert find_active() is None

    @patch("trcc.core.instance._gui_running", return_value=True)
    @patch("trcc.core.instance._api_running", return_value=True)
    def test_gui_takes_priority_over_api(self, _api, _gui):
        """GUI > API priority."""
        assert find_active() == InstanceKind.GUI
