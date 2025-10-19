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


"""Pytest-wide defaulting config for Picard tests.

Why this is necessary:
- Tests do not instantiate the full application, so settings are not
  registered and the `Option` registry may be incomplete during import.
- Adding new settings can cause KeyError in modules imported by certain
  test flows when they access `config.setting[...]`.

What this conftest currently does:
- Ensures option registration is loaded and installs a minimal, dict-like
  config for `setting`/`persist`/`profiles`.
- For registered options it falls back to their default; for unknown keys it
  raises KeyError (preserving tests that expect missing keys).
- Overrides `picard.config.get_config` and module-level exports to point to
  the fake config, and updates `PicardTestCase.init_config` accordingly.
"""

from contextlib import suppress
from types import SimpleNamespace

import pytest


def _make_defaulting_section(section_name, initial=None):
    """Create a dict-like settings section that defaults to Option defaults.

    The object supports dict access, plus `raw_value(name, qtype=None)` and
    `key(name)` methods used across the codebase.
    """

    class _Section(dict):
        def __init__(self, name, data=None):
            super().__init__(data or {})
            self._section_name = name

        def __getitem__(self, name):
            if dict.__contains__(self, name):
                return dict.__getitem__(self, name)
            # Late import to ensure Option registry is available
            from picard.config import Option

            opt = Option.get(self._section_name, name)
            if opt is not None:
                return opt.default
            raise KeyError(name)

        def raw_value(self, name, qtype=None):  # qtype kept for API compatibility
            return dict.get(self, name)

        def key(self, name):
            return f"{self._section_name}/{name}"

        def remove(self, name):
            with suppress(KeyError):
                del self[name]

    return _Section(section_name, initial)


@pytest.fixture(autouse=True)
def _install_defaulting_config(monkeypatch):
    """Install a defaulting config for tests.

    This avoids KeyError when new settings are added by falling back
    to the defaults declared in `picard.options` (Option registry).
    """

    # Ensure options are registered so Option registry has defaults
    import picard.config as cfg_mod
    import picard.options  # noqa: F401

    setting = _make_defaulting_section("setting")
    persist = _make_defaulting_section("persist")
    profiles = _make_defaulting_section("profiles")

    fake_config = SimpleNamespace(setting=setting, persist=persist, profiles=profiles)

    # Expose module-level aliases commonly used in code/tests
    monkeypatch.setattr(cfg_mod, "config", fake_config, raising=False)
    monkeypatch.setattr(cfg_mod, "setting", setting, raising=False)
    monkeypatch.setattr(cfg_mod, "persist", persist, raising=False)
    monkeypatch.setattr(cfg_mod, "profiles", profiles, raising=False)

    # Provide get_config() that returns our fake config unless overridden by other fixtures
    monkeypatch.setattr(cfg_mod, "get_config", lambda: fake_config, raising=False)

    # Ensure required profile keys exist for UI initialization paths
    try:
        from picard.config import SettingConfigSection

        profiles[SettingConfigSection.PROFILES_KEY] = []
        profiles[SettingConfigSection.SETTINGS_KEY] = {}
    except Exception:
        # If import fails here in early test bootstrap, skip; tests that need it will set it up
        pass

    # Provide commonly accessed simple settings to avoid KeyError in action creation
    setting['username'] = ''

    # Patch PicardTestCase.init_config to use our defaulting config as well
    with suppress(ModuleNotFoundError):
        import test.picardtestcase as ptc

        def _init_config_override():
            cfg_mod.config = fake_config
            cfg_mod.setting = setting
            cfg_mod.persist = persist
            cfg_mod.profiles = profiles

        monkeypatch.setattr(ptc.PicardTestCase, "init_config", staticmethod(_init_config_override), raising=False)

    # Yield control to test session
    yield


@pytest.fixture(scope="session", autouse=True)
def _install_qapplication_and_tagger():
    """Provide a minimal Qt application and a fake Tagger for tests.

    Many components access QCoreApplication.instance() as the Tagger (emitting
    signals like tagger_stats_changed). Provide a simple object exposing the
    required attributes to satisfy those interactions for unit tests.
    """
    import os
    from typing import cast

    from PyQt6 import QtCore
    from PyQt6.QtWidgets import QApplication

    # Offscreen to avoid requiring a display in CI
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    class _FakeSignal:
        def emit(self, *args, **kwargs):
            return None

        def connect(self, *args, **kwargs):
            return None

    class _FakeTagger:
        def __init__(self):
            self.tagger_stats_changed = _FakeSignal()
            self.listen_port_changed = _FakeSignal()
            self.webservice = SimpleNamespace(
                num_pending_web_requests=0,
                remove_task=lambda *_: None,
                manager=SimpleNamespace(
                    authenticationRequired=_FakeSignal(),
                    proxyAuthenticationRequired=_FakeSignal(),
                ),
            )
            self.save_thread_pool = None
            self.stopping = False
            self.files = {}
            self.albums = {}
            self.is_wayland = False
            self.pluginmanager = SimpleNamespace(updates_available=SimpleNamespace(connect=lambda *_: None))
            self.lookup_cd = lambda *args, **kwargs: None
            self.autoupdate_enabled = False
            self._no_restore = False

        def clipboard(self):
            return SimpleNamespace(setMimeData=lambda *_: None)

    tagger = _FakeTagger()
    # Monkeypatch the global instance lookup to return our fake tagger
    QtCore.QCoreApplication.instance = lambda: tagger  # type: ignore[assignment]
    return cast(QApplication, app)
