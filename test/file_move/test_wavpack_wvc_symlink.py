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

"""Tests for WavPack file correction file handling with symlink mode."""

from picard.formats.apev2 import WavPackFile

import pytest


class DummyConfig:
    def __init__(self, **settings):
        self.setting = settings


@pytest.fixture(autouse=True)
def isolate_config(monkeypatch):
    dummy = DummyConfig(rename_files=True, move_files=False, symlink_files=True)
    monkeypatch.setattr('picard.formats.apev2.get_config', lambda: dummy)
    return dummy


def test_wvc_symlink_invoked(monkeypatch, isolate_config):
    file = WavPackFile('/music/a.wv')
    # Pretend correction file exists
    monkeypatch.setattr('picard.formats.apev2.isfile', lambda p: True)
    created = []
    # Avoid real filesystem directory creation and capture symlink call via File helpers
    monkeypatch.setattr('picard.file.File._ensure_parent_dir', staticmethod(lambda *_: None))
    monkeypatch.setattr('picard.file.File._create_symlink', staticmethod(lambda src, dst: created.append((src, dst))))
    # get_available_filename should be identity for deterministic assertion
    monkeypatch.setattr('picard.formats.apev2.get_available_filename', lambda new, _old: new)
    # Ensure config reports symlink mode enabled
    isolate_config.setting['symlink_files'] = True

    file._move_or_rename_wvc('/src/a.wv', '/dest/a.wv')
    assert created == [('/src/a.wvc', '/dest/a.wvc')]
