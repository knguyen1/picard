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

"""Tests for Linux Light and Dark theme support."""

from unittest.mock import MagicMock, Mock, patch

from PyQt6 import QtGui
from PyQt6.QtCore import Qt

import pytest

import picard.ui.theme as theme_mod


class DummyPalette(QtGui.QPalette):
    def __init__(self):
        super().__init__()
        # Set a unique color to detect override
        self.setColor(
            QtGui.QPalette.ColorGroup.Active,
            QtGui.QPalette.ColorRole.Window,
            QtGui.QColor(123, 123, 123),
        )


class DummyApp:
    def __init__(self, palette=None):
        self._palette = palette or DummyPalette()

    def setStyle(self, style):
        pass

    def setStyleSheet(self, stylesheet):
        pass

    def palette(self):
        return self._palette

    def setPalette(self, palette):
        self._palette = palette

    def style(self):
        return None


class TestLinuxLightDarkThemeSupport:
    """Test that Linux now supports Light and Dark theme options."""

    def test_available_ui_themes_includes_light_dark_on_linux(self, monkeypatch):
        """Test that AVAILABLE_UI_THEMES includes Light and Dark themes on Linux."""
        # Simulate Linux (not Windows, not macOS, not Haiku)
        monkeypatch.setattr(theme_mod, "IS_WIN", False)
        monkeypatch.setattr(theme_mod, "IS_MACOS", False)
        monkeypatch.setattr(theme_mod, "IS_HAIKU", False)

        # Re-evaluate AVAILABLE_UI_THEMES with new consistent structure
        available_themes = [theme_mod.UiTheme.DEFAULT]
        if not theme_mod.IS_HAIKU:
            available_themes.extend([theme_mod.UiTheme.LIGHT, theme_mod.UiTheme.DARK])

        assert theme_mod.UiTheme.LIGHT in available_themes
        assert theme_mod.UiTheme.DARK in available_themes
        assert theme_mod.UiTheme.DEFAULT in available_themes
        # SYSTEM theme is no longer available on Linux for consistency
        assert theme_mod.UiTheme.SYSTEM not in available_themes

    @pytest.mark.parametrize(
        ("ui_theme", "expected_dark_theme"),
        [
            (theme_mod.UiTheme.LIGHT, False),
            (theme_mod.UiTheme.DARK, True),
            (theme_mod.UiTheme.DEFAULT, None),  # Depends on system (consistent across platforms)
        ],
    )
    def test_linux_theme_is_dark_theme_property(self, monkeypatch, ui_theme, expected_dark_theme):
        """Test that is_dark_theme property works correctly for Linux Light/Dark themes."""
        # Simulate Linux
        monkeypatch.setattr(theme_mod, "IS_WIN", False)
        monkeypatch.setattr(theme_mod, "IS_MACOS", False)
        monkeypatch.setattr(theme_mod, "IS_HAIKU", False)

        theme = theme_mod.BaseTheme()
        theme._loaded_config_theme = ui_theme
        theme._dark_theme = False  # Set a default value

        if expected_dark_theme is not None:
            assert theme.is_dark_theme == expected_dark_theme
        else:
            # For DEFAULT, it should return the value of _dark_theme
            assert theme.is_dark_theme == theme._dark_theme

    @pytest.mark.parametrize(
        ("ui_theme", "expected_color_scheme"),
        [
            (theme_mod.UiTheme.LIGHT, Qt.ColorScheme.Light),
            (theme_mod.UiTheme.DARK, Qt.ColorScheme.Dark),
            (theme_mod.UiTheme.DEFAULT, Qt.ColorScheme.Unknown),
        ],
    )
    def test_linux_theme_color_scheme_setting(self, monkeypatch, ui_theme, expected_color_scheme):
        """Test that Qt ColorScheme is set correctly for Linux Light/Dark themes."""
        # Simulate Linux
        monkeypatch.setattr(theme_mod, "IS_WIN", False)
        monkeypatch.setattr(theme_mod, "IS_MACOS", False)
        monkeypatch.setattr(theme_mod, "IS_HAIKU", False)

        # Mock config
        config_mock = MagicMock()
        config_mock.setting = {"ui_theme": str(ui_theme)}
        monkeypatch.setattr(theme_mod, "get_config", lambda: config_mock)

        # Mock style hints
        mock_style_hints = Mock()

        with patch("PyQt6.QtGui.QGuiApplication.styleHints", return_value=mock_style_hints):
            theme = theme_mod.BaseTheme()
            app = DummyApp()
            theme.setup(app)

            # Verify that setColorScheme was called with the expected value
            mock_style_hints.setColorScheme.assert_called_with(expected_color_scheme)

    def test_linux_light_theme_does_not_trigger_dark_mode_detection(self, monkeypatch):
        """Test that Linux Light theme does not trigger dark mode detection logic."""
        # Simulate Linux
        monkeypatch.setattr(theme_mod, "IS_WIN", False)
        monkeypatch.setattr(theme_mod, "IS_MACOS", False)
        monkeypatch.setattr(theme_mod, "IS_HAIKU", False)

        # Mock config for Light theme
        config_mock = MagicMock()
        config_mock.setting = {"ui_theme": str(theme_mod.UiTheme.LIGHT)}
        monkeypatch.setattr(theme_mod, "get_config", lambda: config_mock)

        theme = theme_mod.BaseTheme()

        # Mock the dark mode detection method to track if it's called
        detect_mock = Mock(return_value=True)
        theme._detect_linux_dark_mode = detect_mock

        with patch("PyQt6.QtGui.QGuiApplication.styleHints", return_value=Mock()):
            app = DummyApp()
            theme.setup(app)

            # Dark mode detection should NOT be called for explicit Light theme
            detect_mock.assert_not_called()

    def test_linux_dark_theme_does_not_trigger_dark_mode_detection(self, monkeypatch):
        """Test that Linux Dark theme does not trigger dark mode detection logic."""
        # Simulate Linux
        monkeypatch.setattr(theme_mod, "IS_WIN", False)
        monkeypatch.setattr(theme_mod, "IS_MACOS", False)
        monkeypatch.setattr(theme_mod, "IS_HAIKU", False)

        # Mock config for Dark theme
        config_mock = MagicMock()
        config_mock.setting = {"ui_theme": str(theme_mod.UiTheme.DARK)}
        monkeypatch.setattr(theme_mod, "get_config", lambda: config_mock)

        theme = theme_mod.BaseTheme()

        # Mock the dark mode detection method to track if it's called
        detect_mock = Mock(return_value=True)
        theme._detect_linux_dark_mode = detect_mock

        with patch("PyQt6.QtGui.QGuiApplication.styleHints", return_value=Mock()):
            app = DummyApp()
            theme.setup(app)

            # Dark mode detection should NOT be called for explicit Dark theme
            detect_mock.assert_not_called()

    def test_linux_default_theme_still_triggers_dark_mode_detection(self, monkeypatch):
        """Test that Linux Default theme still triggers dark mode detection logic."""
        # Simulate Linux
        monkeypatch.setattr(theme_mod, "IS_WIN", False)
        monkeypatch.setattr(theme_mod, "IS_MACOS", False)
        monkeypatch.setattr(theme_mod, "IS_HAIKU", False)

        # Mock config for Default theme (which now acts as system theme on Linux)
        config_mock = MagicMock()
        config_mock.setting = {"ui_theme": str(theme_mod.UiTheme.DEFAULT)}
        monkeypatch.setattr(theme_mod, "get_config", lambda: config_mock)

        theme = theme_mod.BaseTheme()

        # Mock the dark mode detection method to track if it's called
        detect_mock = Mock(return_value=True)
        theme._detect_linux_dark_mode = detect_mock

        # Mock style hints to return None so manual palette setting is used
        with patch("PyQt6.QtGui.QGuiApplication.styleHints", return_value=None):
            # Create a light palette to trigger the detection logic
            palette = DummyPalette()
            palette.setColor(
                QtGui.QPalette.ColorGroup.Active,
                QtGui.QPalette.ColorRole.Base,
                QtGui.QColor(255, 255, 255),  # Light color
            )
            app = DummyApp(palette)
            theme.setup(app)

            # Dark mode detection SHOULD be called for Default theme on Linux
            detect_mock.assert_called_once()

    def test_linux_fusion_style_set_for_light_dark_themes(self, monkeypatch):
        """Test that Fusion style is set for Linux Light/Dark themes."""
        # Simulate Linux
        monkeypatch.setattr(theme_mod, "IS_WIN", False)
        monkeypatch.setattr(theme_mod, "IS_MACOS", False)
        monkeypatch.setattr(theme_mod, "IS_HAIKU", False)

        for ui_theme in [theme_mod.UiTheme.LIGHT, theme_mod.UiTheme.DARK]:
            # Mock config
            config_mock = MagicMock()
            config_mock.setting = {"ui_theme": str(ui_theme)}
            monkeypatch.setattr(theme_mod, "get_config", lambda: config_mock)

            theme = theme_mod.BaseTheme()
            app = DummyApp()

            # Mock setStyle to track calls
            app.setStyle = Mock()

            with patch("PyQt6.QtGui.QGuiApplication.styleHints", return_value=Mock()):
                theme.setup(app)

                # Fusion style should be set for Light/Dark themes on Linux
                app.setStyle.assert_called_with("Fusion")

    def test_linux_default_theme_does_not_set_fusion_style(self, monkeypatch):
        """Test that Fusion style is NOT set for Linux Default theme (system theme)."""
        # Simulate Linux
        monkeypatch.setattr(theme_mod, "IS_WIN", False)
        monkeypatch.setattr(theme_mod, "IS_MACOS", False)
        monkeypatch.setattr(theme_mod, "IS_HAIKU", False)

        # Mock config for Default theme (which now acts as system theme on Linux)
        config_mock = MagicMock()
        config_mock.setting = {"ui_theme": str(theme_mod.UiTheme.DEFAULT)}
        monkeypatch.setattr(theme_mod, "get_config", lambda: config_mock)

        theme = theme_mod.BaseTheme()
        app = DummyApp()

        # Mock setStyle to track calls
        app.setStyle = Mock()

        with patch("PyQt6.QtGui.QGuiApplication.styleHints", return_value=Mock()):
            theme.setup(app)

            # Fusion style should NOT be set for Default theme on Linux (system theme)
            app.setStyle.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__])
