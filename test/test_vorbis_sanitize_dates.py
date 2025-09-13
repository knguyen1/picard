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

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from picard import config
from picard.formats.vorbis import OggVorbisFile
from picard.metadata import Metadata

import pytest  # type: ignore


@pytest.fixture
def patched_get_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Initialize minimal config and patch get_config(); no teardown needed.

    Mirrors the approach used in test_date_sanitization_setting.
    """
    fake = SimpleNamespace(setting={}, persist={}, profiles={})
    config.config = fake
    config.setting = fake.setting
    config.persist = fake.persist
    config.profiles = fake.profiles
    monkeypatch.setattr('picard.config.get_config', lambda: fake, raising=True)
    # Minimal defaults required by vorbis save/load code paths
    config.setting.update(
        {
            'disable_date_sanitization_formats': [],
            'clear_existing_tags': False,
            'preserve_images': False,
            'remove_id3_from_flac': False,
            'fix_missing_seekpoints_flac': False,
            'save_images_to_tags': False,
            'embed_only_one_front_image': False,
            'remove_images_from_tags': False,
            'rating_user_email': '',
            'rating_steps': 6,
        }
    )
    return None


class _FakeMutagenVorbis:
    """Minimal mutagen-like fake consumed by VCommentFile.

    - Accepts construction with a filename
    - Exposes .tags as a dict[str, list[str]]
    - Has .info attribute (fields unused in these tests)
    - Provides add_tags() and save() used during _save
    """

    last_instance: _FakeMutagenVorbis | None = None
    next_tags: dict[str, list[str]] | None = None

    def __init__(self, filename: str) -> None:  # noqa: ARG002 (test fake)
        type(self).last_instance = self
        # Start with next_tags if provided to seed instance state
        self.tags: dict[str, list[str]] = (type(self).next_tags or {}).copy()
        self.info = SimpleNamespace()

    def add_tags(self) -> None:
        if self.tags is None:  # pragma: no cover - defensive
            self.tags = {}

    def save(self, **kwargs: Any) -> None:  # noqa: ARG002 (test fake)
        return None

    def __getitem__(self, key: str) -> list[str]:
        # Provide mapping-style access used by Vorbis loader for legacy COVERART
        try:
            return self.tags[key]
        except KeyError:
            lowered = key.lower()
            if lowered in self.tags:
                return self.tags[lowered]
            raise KeyError(key) from None


@pytest.mark.parametrize(
    ('disabled', 'input_date', 'expected_when_enabled'),
    [
        ([], '2005-12-00', '2005-12'),
        ([], '2005-00-00', '2005'),
        ([], '0000-00-00', ''),
        ([], '2005-00-12', '2005-00-12'),
        ([], '0000-00-12', '0000-00-12'),
        (['vorbis'], '2005-12-00', '2005-12'),  # used only to assert disabled path keeps raw
    ],
)
def test_vorbis_load_respects_date_sanitization_setting(
    patched_get_config: None,
    monkeypatch: pytest.MonkeyPatch,
    disabled: list[str],
    input_date: str,
    expected_when_enabled: str,
) -> None:
    # Arrange
    settings = cast(dict[str, Any], config.setting)
    settings['disable_date_sanitization_formats'] = disabled

    # Monkeypatch the backend class used by vorbis to our fake
    # Seed tags via class variable consumed by __init__
    _FakeMutagenVorbis.next_tags = {'date': [input_date]}
    monkeypatch.setattr(OggVorbisFile, '_File', _FakeMutagenVorbis, raising=True)
    # Avoid calling into File._info (requires full File initialization)
    monkeypatch.setattr(OggVorbisFile, '_info', lambda self, metadata, file: None, raising=True)

    # Act: call _load directly
    vorbis_file = OggVorbisFile.__new__(OggVorbisFile)
    metadata = vorbis_file._load('dummy.ogg')

    # Assert
    if vorbis_file.is_date_sanitization_enabled():
        assert metadata['date'] == expected_when_enabled
    else:
        assert metadata['date'] == input_date


@pytest.mark.parametrize(
    ('disabled', 'input_date', 'expected_saved'),
    [
        ([], '2005-12-00', '2005-12'),
        ([], '2005-00-00', '2005'),
        ([], '0000-00-00', ''),
        (['vorbis'], '2005-12-00', '2005-12-00'),
    ],
)
def test_vorbis_save_respects_date_sanitization_setting(
    patched_get_config: None, monkeypatch: pytest.MonkeyPatch, disabled: list[str], input_date: str, expected_saved: str
) -> None:
    # Arrange
    settings = cast(dict[str, Any], config.setting)
    settings.update(
        {
            'disable_date_sanitization_formats': disabled,
            'clear_existing_tags': False,
            'preserve_images': False,
            'fix_missing_seekpoints_flac': False,
            'remove_id3_from_flac': False,
        }
    )
    monkeypatch.setattr(OggVorbisFile, '_File', _FakeMutagenVorbis, raising=True)
    # Avoid File._info dependencies in potential internal helpers
    monkeypatch.setattr(OggVorbisFile, '_info', lambda self, metadata, file: None, raising=True)

    # Prepare metadata to be saved
    md = Metadata()
    md['date'] = input_date

    vorbis_file = OggVorbisFile.__new__(OggVorbisFile)

    # Act
    vorbis_file._save('dummy.ogg', md)

    # Assert: fake backend captured saved tags; keys are uppercased by writer
    saved = _FakeMutagenVorbis.last_instance
    assert saved is not None
    assert saved.tags.get('DATE') == [expected_saved]
