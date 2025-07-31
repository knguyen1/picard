# -*- coding: utf-8 -*-
#
# Picard, the next-generation MusicBrainz tagger
#
# Copyright (C) 2019-2022, 2024-2025 Philipp Wolfer
# Copyright (C) 2020-2021 Gabriel Ferreira
# Copyright (C) 2021-2024 Laurent Monin
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

"""Dark mode detection for Linux desktop environments using D-Bus with subprocess fallback."""

import os
from pathlib import Path
import subprocess  # noqa: S404

# D-Bus imports - PyQt6 is already a dependency
from PyQt6.QtDBus import (
    QDBusConnection,
    QDBusInterface,
    QDBusMessage,
)

from picard import log


class DBusThemeDetector:
    """D-Bus-based theme detection for Linux desktop environments."""

    def __init__(self):
        self.session_bus = None
        self.portal_interface = None
        self.gnome_interface = None
        self._initialize_dbus()

    def _initialize_dbus(self) -> None:
        """Initialize D-Bus connection and interfaces."""
        try:
            self.session_bus = QDBusConnection.sessionBus()
            if not self.session_bus.isConnected():
                return

            # Initialize freedesktop.org settings portal interface
            self.portal_interface = QDBusInterface(
                "org.freedesktop.portal.Desktop",
                "/org/freedesktop/portal/desktop",
                "org.freedesktop.portal.Settings",
                self.session_bus,
            )

            # Initialize GNOME settings interface
            self.gnome_interface = QDBusInterface(
                "ca.desrt.dconf",
                "/ca/desrt/dconf/Writer/user",
                "ca.desrt.dconf.Writer",
                self.session_bus,
            )

        except Exception:  # noqa: BLE001
            self.session_bus = None
            self.portal_interface = None
            self.gnome_interface = None

    def detect_freedesktop_portal_color_scheme(self) -> bool | None:
        """
        Detect color scheme using org.freedesktop.portal.Settings interface.

        Returns
        -------
            True for dark theme, False for light theme, None if unavailable
        """
        try:
            if not self.portal_interface or not self.portal_interface.isValid():
                return None
            # Call the Read method to get color-scheme setting
            reply = self.portal_interface.call("Read", "org.freedesktop.appearance", "color-scheme")

            if reply.type() == QDBusMessage.MessageType.ErrorMessage:
                return None

            # The reply should contain a variant with the color scheme value
            # 0 = no preference, 1 = prefer dark, 2 = prefer light
            value = reply.arguments()[0] if reply.arguments() else None

            if value == 1:
                return True
            if value == 2:
                return False

        except (RuntimeError, AttributeError, TypeError):
            return None
        else:
            return None

    def detect_gnome_color_scheme_dbus(self) -> bool | None:
        """
        Detect GNOME color scheme using D-Bus dconf interface.

        Returns
        -------
            True for dark theme, False for light theme, None if unavailable
        """
        try:
            if not self.gnome_interface or not self.gnome_interface.isValid():
                return None
            # Get the color-scheme property from org.gnome.desktop.interface using dconf
            reply = self.gnome_interface.call("Read", "/org/gnome/desktop/interface/color-scheme")

            if reply.type() != QDBusMessage.MessageType.ErrorMessage:
                value = reply.arguments()[0] if reply.arguments() else None
                if value and isinstance(value, str) and "dark" in value.lower():
                    return True
                if value:
                    return False

        except (RuntimeError, AttributeError, TypeError):
            pass

        # Try gtk-theme as fallback
        try:
            reply = self.gnome_interface.call("Read", "/org/gnome/desktop/interface/gtk-theme")

            if reply.type() != QDBusMessage.MessageType.ErrorMessage:
                value = reply.arguments()[0] if reply.arguments() else None
                if value and isinstance(value, str) and "dark" in value.lower():
                    return True

        except (RuntimeError, AttributeError, TypeError):
            pass

        return None


# Global D-Bus detector instance
_dbus_detector = None


def get_dbus_detector() -> DBusThemeDetector:
    """Get or create the global D-Bus theme detector instance."""
    global _dbus_detector
    if _dbus_detector is None:
        _dbus_detector = DBusThemeDetector()
    return _dbus_detector


def detect_freedesktop_color_scheme_dbus() -> bool:
    """Detect dark mode using D-Bus freedesktop.org portal interface."""
    try:
        detector = get_dbus_detector()
        result = detector.detect_freedesktop_portal_color_scheme()
    except (RuntimeError, AttributeError, TypeError):
        return False
    else:
        return result is True


def detect_gnome_color_scheme_dbus() -> bool:
    """Detect GNOME color scheme using D-Bus interface."""
    try:
        detector = get_dbus_detector()
        result = detector.detect_gnome_color_scheme_dbus()
    except (RuntimeError, AttributeError, TypeError):
        return False
    else:
        return result is True


def gsettings_get(key: str) -> str | None:
    """Get a gsettings value as a string or None."""
    try:
        result = subprocess.run(
            [
                "gsettings",
                "get",
                "org.gnome.desktop.interface",
                key,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().strip("'\"")
    except (subprocess.CalledProcessError, FileNotFoundError):
        log.debug(f"gsettings get {key} failed.")
        return None


def detect_gnome_color_scheme_dark() -> bool:
    """Detect if GNOME color-scheme is set to dark."""
    # Try D-Bus first (secure method)
    try:
        detector = get_dbus_detector()
        result = detector.detect_gnome_color_scheme_dbus()
        if result is not None:
            return result
    except Exception:  # noqa: BLE001
        log.debug("Unable to detect gnome color scheme with dbus.")

    # Fallback to subprocess method (legacy support)
    value = gsettings_get("color-scheme")
    if value and "dark" in value.lower():
        log.debug("Detected GNOME color-scheme: dark")
        return True
    return False


def detect_gnome_gtk_theme_dark() -> bool:
    """Detect if GNOME gtk-theme is set to dark."""
    theme = gsettings_get("gtk-theme")
    if theme and "dark" in theme.lower():
        log.debug(f"Detected GNOME gtk-theme: {theme} (dark)")
        return True
    return False


def detect_kde_colorscheme_dark() -> bool:
    """Detect if KDE ColorScheme is set to dark."""
    kdeglobals = Path.home() / ".config" / "kdeglobals"
    if kdeglobals.exists():
        try:
            with kdeglobals.open() as f:
                for line in f:
                    if line.strip().startswith("ColorScheme="):
                        scheme = line.split("=", 1)[1].strip().lower()
                        if "dark" in scheme:
                            log.debug(f"Detected KDE ColorScheme: {scheme} (dark)")
                            return True
        except OSError as e:
            log.debug(f"KDE ColorScheme detection failed: {e}")
    return False


def detect_xfce_dark_theme() -> bool:
    """Detect if XFCE theme is set to dark."""
    try:
        result = subprocess.run(  # nosec B603 B607
            [
                "xfconf-query",
                "-c",
                "xsettings",
                "-p",
                "/Net/ThemeName",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        theme = result.stdout.strip().lower()
        if "dark" in theme:
            log.debug(f"Detected XFCE theme: {theme} (dark)")
            return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        log.debug("xfconf-query detection failed.")
    return False


def detect_lxqt_dark_theme() -> bool:
    """Detect if LXQt theme is set to dark."""
    lxqt_conf = Path.home() / ".config" / "lxqt" / "session.conf"
    if lxqt_conf.exists():
        try:
            with lxqt_conf.open() as f:
                for line in f:
                    if line.strip().startswith("theme="):
                        theme = line.split("=", 1)[1].strip().lower()
                        if "dark" in theme:
                            log.debug(f"Detected LXQt theme: {theme} (dark)")
                            return True
        except OSError as e:
            log.debug(f"LXQt theme detection failed: {e}")
    return False


def detect_freedesktop_color_scheme_dark() -> bool:
    """Detect dark mode using org.freedesktop.appearance.color-scheme (XDG portal, cross-desktop)."""
    # Try D-Bus first (secure method)
    try:
        detector = get_dbus_detector()
        result = detector.detect_freedesktop_portal_color_scheme()
        if result is not None:
            return result
    except Exception:  # noqa: BLE001
        log.debug("Unable to detect `freedesktop` color scheme with dbus.")

    # Fallback to subprocess method (legacy support)
    try:
        result = subprocess.run(  # nosec B603 B607
            [
                "gsettings",
                "get",
                "org.freedesktop.appearance",
                "color-scheme",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        value = result.stdout.strip().strip("'\"")
        if value == "1":
            log.debug("Detected org.freedesktop.appearance.color-scheme: dark (1)")
            return True
        if value == "0":
            log.debug("Detected org.freedesktop.appearance.color-scheme: light (0)")
            return False
    except (subprocess.CalledProcessError, FileNotFoundError):
        log.debug("gsettings get org.freedesktop.appearance.color-scheme failed.")
    return False


def get_current_desktop_environment() -> str:
    """Detect the current desktop environment (DE) as a lowercase string."""
    de = os.environ.get("XDG_CURRENT_DESKTOP")
    if de:
        return de.lower()
    # Fallbacks for KDE, XFCE, LXQt
    if os.environ.get("KDE_FULL_SESSION") == "true":
        return "kde"
    if os.environ.get("XDG_SESSION_DESKTOP"):
        return os.environ["XDG_SESSION_DESKTOP"].lower()
    if os.environ.get("DESKTOP_SESSION"):
        return os.environ["DESKTOP_SESSION"].lower()
    return ""


# Wrappers for DE-specific detection


def detect_gnome_dark_wrapper() -> bool:
    """Detect dark mode for GNOME or Unity desktop environments."""
    if get_current_desktop_environment() in {"gnome", "unity"}:
        return detect_gnome_color_scheme_dark() or detect_gnome_gtk_theme_dark()
    return False


def detect_kde_dark_wrapper() -> bool:
    """Detect dark mode for KDE desktop environment."""
    if get_current_desktop_environment() == "kde":
        return detect_kde_colorscheme_dark()
    return False


def detect_xfce_dark_wrapper() -> bool:
    """Detect dark mode for XFCE desktop environment."""
    if get_current_desktop_environment() == "xfce":
        return detect_xfce_dark_theme()
    return False


def detect_lxqt_dark_wrapper() -> bool:
    """Detect dark mode for LXQt desktop environment."""
    if get_current_desktop_environment() == "lxqt":
        return detect_lxqt_dark_theme()
    return False


def get_linux_dark_mode_strategies() -> list:
    """Return the list of dark mode detection strategies in order of priority."""
    return [
        # Pure D-Bus methods (will gracefully fail if D-Bus unavailable)
        detect_freedesktop_color_scheme_dbus,
        detect_gnome_color_scheme_dbus,
        # Hybrid methods (D-Bus with subprocess fallback)
        detect_freedesktop_color_scheme_dark,
        detect_gnome_dark_wrapper,
        detect_kde_dark_wrapper,
        detect_xfce_dark_wrapper,
        detect_lxqt_dark_wrapper,
    ]
