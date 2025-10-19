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

"""Tests for settings dispatch in MainWindow."""

from picard.ui.enums import MainAction
from picard.ui.mainwindow.__init__ import MainWindow


class DummyAction:
    def __init__(self):
        self._checked = False
        self._enabled = True

    def setChecked(self, v):
        self._checked = bool(v)

    def isChecked(self):
        return self._checked

    def setEnabled(self, v):
        self._enabled = bool(v)

    def isEnabled(self):
        return self._enabled


def build_window(monkeypatch):
    # Avoid heavy UI initialization not needed for action toggle tests
    monkeypatch.setattr('picard.ui.mainwindow.__init__.MainWindow.setupUi', lambda self: None)
    w = MainWindow(disable_player=True)
    # Override actions to dummy controllables
    w.actions[MainAction.ENABLE_RENAMING] = DummyAction()
    w.actions[MainAction.ENABLE_MOVING] = DummyAction()
    w.actions[MainAction.ENABLE_TAG_SAVING] = DummyAction()
    w.actions[MainAction.ENABLE_SYMLINKING] = DummyAction()
    return w


def test_symlink_dispatch_enforces_move_disable(monkeypatch):
    w = build_window(monkeypatch)

    # Enable move first to ensure the handler unchecks it
    w.actions[MainAction.ENABLE_MOVING].setChecked(True)
    w.handle_settings_changed('symlink_files', False, True)

    assert w.actions[MainAction.ENABLE_MOVING].isEnabled() is False
    assert w.actions[MainAction.ENABLE_MOVING].isChecked() is False
    assert w.actions[MainAction.ENABLE_SYMLINKING].isChecked() is True


def test_move_toggle_updates_action(monkeypatch):
    w = build_window(monkeypatch)
    w.handle_settings_changed('move_files', False, True)
    assert w.actions[MainAction.ENABLE_MOVING].isChecked() is True


def test_rename_toggle_updates_action(monkeypatch):
    w = build_window(monkeypatch)
    w.handle_settings_changed('rename_files', False, True)
    assert w.actions[MainAction.ENABLE_RENAMING].isChecked() is True


def test_enable_tag_saving_toggle_updates_action(monkeypatch):
    w = build_window(monkeypatch)
    w.handle_settings_changed('enable_tag_saving', False, True)
    assert w.actions[MainAction.ENABLE_TAG_SAVING].isChecked() is True
