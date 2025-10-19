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

"""Tests for symlink file operations."""

import errno
from unittest.mock import MagicMock

from picard.file import File
from picard.metadata import Metadata

import pytest


class DummyConfig:
    def __init__(self, **settings):
        # Ensure defaults for keys accessed in code paths under test
        defaults = {
            'rename_files': False,
            'move_files': False,
            'symlink_files': False,
            'move_files_to': '/dest',
            'windows_compatibility': False,
            'windows_long_paths': True,
            'delete_empty_dirs': False,
            'save_images_to_files': False,
        }
        defaults.update(settings)
        self.setting = defaults


@pytest.fixture()
def file_obj(monkeypatch):
    # Create a lightweight File instance without touching disk
    monkeypatch.setattr(File, '_save', lambda *args, **kwargs: None)
    obj = File('/src/file.mp3')
    # Tagger is provided globally via conftest by overriding QCoreApplication.instance()
    obj.orig_metadata = Metadata()
    obj.metadata = Metadata()
    return obj


def test_relocate_no_changes_returns_original(monkeypatch, file_obj):
    config = DummyConfig(rename_files=False, move_files=False, symlink_files=False)
    target = file_obj._relocate_if_required('/src/file.mp3', Metadata(), config)
    assert target == '/src/file.mp3'


def test_relocate_symlink_creates_link(monkeypatch, file_obj):
    calls = []
    # Make filename computation deterministic
    monkeypatch.setattr(file_obj, 'make_filename', lambda *_: '/dest/Album/file.mp3')
    monkeypatch.setattr(file_obj, '_ensure_parent_dir', lambda p: calls.append(('ensure_dir', p)))
    monkeypatch.setattr(file_obj, '_create_symlink', lambda src, dst: calls.append(('symlink', src, dst)))
    config = DummyConfig(symlink_files=True)

    target = file_obj._relocate_if_required('/src/file.mp3', Metadata(), config)

    assert target == '/dest/Album/file.mp3'
    assert ('ensure_dir', '/dest/Album/file.mp3') in calls
    assert ('symlink', '/src/file.mp3', '/dest/Album/file.mp3') in calls


def test_relocate_symlink_failure_returns_original(monkeypatch, file_obj):
    monkeypatch.setattr(file_obj, 'make_filename', lambda *_: '/dest/Album/file.mp3')
    monkeypatch.setattr(file_obj, '_ensure_parent_dir', lambda *_: None)

    def boom(*_args, **_kwargs):
        raise OSError(errno.EPERM, 'no perms')

    monkeypatch.setattr(file_obj, '_create_symlink', boom)
    config = DummyConfig(symlink_files=True)

    target = file_obj._relocate_if_required('/src/file.mp3', Metadata(), config)
    assert target == '/src/file.mp3'


@pytest.mark.parametrize(
    ('move_files', 'symlink_files', 'expected_dir'),
    [
        (True, False, '/music'),
        (False, True, '/music'),
        (False, False, '/src'),
    ],
)
def test_make_filename_destination_dir(monkeypatch, file_obj, move_files, symlink_files, expected_dir):
    config = DummyConfig(move_files=move_files, symlink_files=symlink_files, move_files_to='/music')
    # Naming script: avoid formatting changes, focus on dir computation
    monkeypatch.setattr('picard.file.get_file_naming_script', lambda *_: None)
    new_path = file_obj.make_filename('/src/file.mp3', Metadata(), config.setting, naming_format=None)
    assert new_path.startswith(expected_dir)


def test_create_symlink_idempotent(monkeypatch, file_obj):
    # Link already points to the same normalized target
    monkeypatch.setattr('os.path.islink', lambda p: True)
    monkeypatch.setattr('os.readlink', lambda p: '/a/b')
    monkeypatch.setattr('os.path.abspath', lambda p: '/a/b')
    os_remove = MagicMock()
    os_symlink = MagicMock()
    monkeypatch.setattr('os.remove', lambda p: os_remove(p))
    monkeypatch.setattr('os.symlink', lambda src, dst, target_is_directory=False: os_symlink(src, dst))

    file_obj._create_symlink('/a/b', '/c/d')
    os_remove.assert_not_called()
    os_symlink.assert_not_called()


def test_create_symlink_existing_not_symlink_raises(monkeypatch, file_obj):
    monkeypatch.setattr('os.path.islink', lambda p: False)
    monkeypatch.setattr('os.path.exists', lambda p: True)
    with pytest.raises(OSError) as exc:
        file_obj._create_symlink('/src/file.mp3', '/dest/file.mp3')
    err = exc.value
    assert isinstance(err, OSError)
    assert getattr(err, 'errno', None) == errno.EEXIST


def test_apply_additional_files_symlink(monkeypatch, file_obj):
    # Directly test the inner application, bypassing gating in _move_additional_files
    created = []
    monkeypatch.setattr('picard.file.get_config', lambda: DummyConfig(symlink_files=True))
    monkeypatch.setattr(file_obj, '_ensure_parent_dir', lambda p: None)
    monkeypatch.setattr('picard.file.get_available_filename', lambda new, _old: new)
    monkeypatch.setattr(file_obj, '_create_symlink', lambda src, dst: created.append((src, dst)))

    file_obj._apply_additional_files_moves([('/old/cover.jpg', '/new/cover.jpg')])
    assert created == [('/old/cover.jpg', '/new/cover.jpg')]
