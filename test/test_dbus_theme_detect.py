# -*- coding: utf-8 -*-
#
# Picard, the next-generation MusicBrainz tagger
#
# Copyright (C) 2025 The MusicBrainz Team
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

"""Tests for D-Bus-based theme detection functionality."""

import unittest
from unittest.mock import Mock, patch

from test.picardtestcase import PicardTestCase

# Mock PyQt6.QtDBus imports for testing on systems without D-Bus
with patch.dict(
    "sys.modules",
    {
        "PyQt6.QtDBus": Mock(),
        "PyQt6.QtDBus.QDBusConnection": Mock(),
        "PyQt6.QtDBus.QDBusInterface": Mock(),
        "PyQt6.QtDBus.QDBusMessage": Mock(),
        "PyQt6.QtDBus.QDBusReply": Mock(),
    },
):
    from picard.ui import theme_detect


class TestDBusThemeDetector(PicardTestCase):
    """Test cases for DBusThemeDetector class."""

    def setUp(self):
        super().setUp()
        # Reset the global detector instance
        theme_detect._dbus_detector = None

    @patch("picard.ui.theme_detect.QDBusConnection")
    def test_dbus_detector_initialization_success(self, mock_connection):
        """Test successful D-Bus detector initialization."""
        # Mock successful D-Bus connection
        mock_session_bus = Mock()
        mock_session_bus.isConnected.return_value = True
        mock_connection.sessionBus.return_value = mock_session_bus

        # Mock interfaces
        mock_portal_interface = Mock()
        mock_portal_interface.isValid.return_value = True
        mock_gnome_interface = Mock()
        mock_gnome_interface.isValid.return_value = True

        with patch("picard.ui.theme_detect.QDBusInterface") as mock_interface:
            mock_interface.side_effect = [mock_portal_interface, mock_gnome_interface]

            detector = theme_detect.DBusThemeDetector()

            assert detector.session_bus is not None
            assert detector.portal_interface is not None
            assert detector.gnome_interface is not None

    @patch("picard.ui.theme_detect.QDBusConnection")
    @patch("picard.ui.theme_detect.QDBusInterface")
    def test_dbus_detector_initialization_unavailable(
        self, mock_interface, mock_connection
    ):
        """Test D-Bus detector initialization when D-Bus connection fails."""
        # Mock D-Bus connection failure by raising exception during initialization
        mock_connection.sessionBus.side_effect = Exception("D-Bus not available")

        detector = theme_detect.DBusThemeDetector()

        assert detector.session_bus is None
        assert detector.portal_interface is None
        assert detector.gnome_interface is None

    @patch("picard.ui.theme_detect.QDBusConnection")
    def test_dbus_detector_initialization_connection_failed(self, mock_connection):
        """Test D-Bus detector initialization when connection fails."""
        # Mock failed D-Bus connection
        mock_session_bus = Mock()
        mock_session_bus.isConnected.return_value = False
        mock_connection.sessionBus.return_value = mock_session_bus

        detector = theme_detect.DBusThemeDetector()

        assert detector.portal_interface is None
        assert detector.gnome_interface is None

    def test_detect_freedesktop_portal_color_scheme_dark(self):
        """Test freedesktop portal color scheme detection returning dark."""
        detector = theme_detect.DBusThemeDetector()

        # Mock valid portal interface
        mock_interface = Mock()
        mock_interface.isValid.return_value = True

        # Mock D-Bus reply for dark theme (value = 1)
        mock_reply = Mock()
        mock_reply.type.return_value = Mock()  # Not an error message
        mock_reply.arguments.return_value = [1]
        mock_interface.call.return_value = mock_reply

        detector.portal_interface = mock_interface

        result = detector.detect_freedesktop_portal_color_scheme()
        assert result

    def test_detect_freedesktop_portal_color_scheme_light(self):
        """Test freedesktop portal color scheme detection returning light."""
        detector = theme_detect.DBusThemeDetector()

        # Mock valid portal interface
        mock_interface = Mock()
        mock_interface.isValid.return_value = True

        # Mock D-Bus reply for light theme (value = 2)
        mock_reply = Mock()
        mock_reply.type.return_value = Mock()  # Not an error message
        mock_reply.arguments.return_value = [2]
        mock_interface.call.return_value = mock_reply

        detector.portal_interface = mock_interface

        result = detector.detect_freedesktop_portal_color_scheme()
        assert not result

    def test_detect_freedesktop_portal_color_scheme_no_preference(self):
        """Test freedesktop portal color scheme detection with no preference."""
        detector = theme_detect.DBusThemeDetector()

        # Mock valid portal interface
        mock_interface = Mock()
        mock_interface.isValid.return_value = True

        # Mock D-Bus reply for no preference (value = 0)
        mock_reply = Mock()
        mock_reply.type.return_value = Mock()  # Not an error message
        mock_reply.arguments.return_value = [0]
        mock_interface.call.return_value = mock_reply

        detector.portal_interface = mock_interface

        result = detector.detect_freedesktop_portal_color_scheme()
        assert result is None

    def test_detect_freedesktop_portal_color_scheme_interface_invalid(self):
        """Test freedesktop portal color scheme detection with invalid interface."""
        detector = theme_detect.DBusThemeDetector()

        # Mock invalid portal interface
        mock_interface = Mock()
        mock_interface.isValid.return_value = False
        detector.portal_interface = mock_interface

        result = detector.detect_freedesktop_portal_color_scheme()
        assert result is None

    def test_detect_freedesktop_portal_color_scheme_dbus_error(self):
        """Test freedesktop portal color scheme detection with D-Bus error."""
        detector = theme_detect.DBusThemeDetector()

        # Mock valid portal interface
        mock_interface = Mock()
        mock_interface.isValid.return_value = True

        # Mock D-Bus error reply
        from PyQt6.QtDBus import QDBusMessage

        mock_reply = Mock()
        mock_reply.type.return_value = QDBusMessage.MessageType.ErrorMessage
        mock_reply.errorMessage.return_value = "Test error"
        mock_interface.call.return_value = mock_reply

        detector.portal_interface = mock_interface

        result = detector.detect_freedesktop_portal_color_scheme()
        assert result is None

    def test_detect_gnome_color_scheme_dbus_dark(self):
        """Test GNOME color scheme detection via D-Bus returning dark."""
        detector = theme_detect.DBusThemeDetector()

        # Mock valid GNOME interface
        mock_interface = Mock()
        mock_interface.isValid.return_value = True

        # Mock D-Bus reply for dark color scheme
        mock_reply = Mock()
        mock_reply.type.return_value = Mock()  # Not an error message
        mock_reply.arguments.return_value = ["prefer-dark"]
        mock_interface.call.return_value = mock_reply

        detector.gnome_interface = mock_interface

        result = detector.detect_gnome_color_scheme_dbus()
        assert result

    def test_detect_gnome_color_scheme_dbus_light(self):
        """Test GNOME color scheme detection via D-Bus returning light."""
        detector = theme_detect.DBusThemeDetector()

        # Mock valid GNOME interface
        mock_interface = Mock()
        mock_interface.isValid.return_value = True

        # Mock D-Bus reply for light color scheme
        mock_reply = Mock()
        mock_reply.type.return_value = Mock()  # Not an error message
        mock_reply.arguments.return_value = ["prefer-light"]
        mock_interface.call.return_value = mock_reply

        detector.gnome_interface = mock_interface

        result = detector.detect_gnome_color_scheme_dbus()
        assert not result

    def test_detect_gnome_color_scheme_dbus_gtk_theme_fallback(self):
        """Test GNOME D-Bus detection falling back to gtk-theme."""
        detector = theme_detect.DBusThemeDetector()

        # Mock valid GNOME interface
        mock_interface = Mock()
        mock_interface.isValid.return_value = True

        # Mock D-Bus error for color-scheme, success for gtk-theme
        from PyQt6.QtDBus import QDBusMessage

        mock_error_reply = Mock()
        mock_error_reply.type.return_value = QDBusMessage.MessageType.ErrorMessage

        mock_success_reply = Mock()
        mock_success_reply.type.return_value = Mock()  # Not an error message
        mock_success_reply.arguments.return_value = ["Adwaita-dark"]

        mock_interface.call.side_effect = [mock_error_reply, mock_success_reply]
        detector.gnome_interface = mock_interface

        result = detector.detect_gnome_color_scheme_dbus()
        assert result


class TestDBusIntegrationFunctions(PicardTestCase):
    """Test cases for D-Bus integration functions."""

    def setUp(self):
        super().setUp()
        # Reset the global detector instance
        theme_detect._dbus_detector = None

    def test_detect_freedesktop_color_scheme_dbus_function(self):
        """Test the detect_freedesktop_color_scheme_dbus function."""
        with patch.object(theme_detect, "get_dbus_detector") as mock_get_detector:
            mock_detector = Mock()
            mock_detector.detect_freedesktop_portal_color_scheme.return_value = True
            mock_get_detector.return_value = mock_detector

            result = theme_detect.detect_freedesktop_color_scheme_dbus()
            assert result

    def test_detect_gnome_color_scheme_dbus_function(self):
        """Test the detect_gnome_color_scheme_dbus function."""
        with patch.object(theme_detect, "get_dbus_detector") as mock_get_detector:
            mock_detector = Mock()
            mock_detector.detect_gnome_color_scheme_dbus.return_value = True
            mock_get_detector.return_value = mock_detector

            result = theme_detect.detect_gnome_color_scheme_dbus()
            assert result

    def test_get_dbus_detector_singleton(self):
        """Test that get_dbus_detector returns a singleton instance."""
        detector1 = theme_detect.get_dbus_detector()
        detector2 = theme_detect.get_dbus_detector()

        assert detector1 is detector2


class TestEnhancedDetectionStrategies(PicardTestCase):
    """Test cases for enhanced detection strategies with D-Bus integration."""

    def setUp(self):
        super().setUp()
        # Reset the global detector instance
        theme_detect._dbus_detector = None

    def test_detect_freedesktop_color_scheme_dark_dbus_priority(self):
        """Test that D-Bus method is tried first in freedesktop detection."""
        with patch.object(theme_detect, "get_dbus_detector") as mock_get_detector:
            mock_detector = Mock()
            mock_detector.detect_freedesktop_portal_color_scheme.return_value = True
            mock_get_detector.return_value = mock_detector

            with patch("subprocess.run") as mock_subprocess:
                result = theme_detect.detect_freedesktop_color_scheme_dark()

                # D-Bus method should be called
                mock_get_detector.assert_called_once()
                # Subprocess should not be called since D-Bus succeeded
                mock_subprocess.assert_not_called()
                assert result

    def test_detect_freedesktop_color_scheme_dark_subprocess_fallback(self):
        """Test subprocess fallback when D-Bus method returns None."""
        with patch.object(theme_detect, "get_dbus_detector") as mock_get_detector:
            mock_detector = Mock()
            mock_detector.detect_freedesktop_portal_color_scheme.return_value = (
                None  # D-Bus method failed
            )
            mock_get_detector.return_value = mock_detector

            with patch("subprocess.run") as mock_subprocess:
                # Mock successful subprocess call
                mock_result = Mock()
                mock_result.stdout = "'1'"
                mock_result.returncode = 0
                mock_subprocess.return_value = mock_result

                result = theme_detect.detect_freedesktop_color_scheme_dark()

                # Both methods should be called
                mock_get_detector.assert_called_once()
                mock_subprocess.assert_called_once()
                assert result

    def test_get_linux_dark_mode_strategies_dbus_priority(self):
        """Test that D-Bus strategies are prioritized in the strategy list."""
        strategies = theme_detect.get_linux_dark_mode_strategies()

        # First two strategies should be pure D-Bus methods
        assert strategies[0] == theme_detect.detect_freedesktop_color_scheme_dbus
        assert strategies[1] == theme_detect.detect_gnome_color_scheme_dbus

        # Traditional methods should follow
        assert theme_detect.detect_freedesktop_color_scheme_dark in strategies
        assert theme_detect.detect_gnome_dark_wrapper in strategies

    def test_get_linux_dark_mode_strategies_no_dbus(self):
        """Test strategy list when D-Bus is not available."""
        strategies = theme_detect.get_linux_dark_mode_strategies()

        # Should include D-Bus methods (they handle failures gracefully)
        assert theme_detect.detect_freedesktop_color_scheme_dbus in strategies
        assert theme_detect.detect_gnome_color_scheme_dbus in strategies

        # Should include traditional methods
        assert theme_detect.detect_freedesktop_color_scheme_dark in strategies
        assert theme_detect.detect_gnome_dark_wrapper in strategies


if __name__ == "__main__":
    unittest.main()
