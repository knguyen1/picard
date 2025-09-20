# -*- coding: utf-8 -*-
#
# Picard, the next-generation MusicBrainz tagger
#
# Copyright (C) 2025 The MusicBrainz Team
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the GNU General Public License Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

"""Factory for creating match quality delegate columns."""

from __future__ import annotations

from PyQt6 import QtCore

from picard.i18n import N_

from picard.ui.columns import ColumnSortType
from picard.ui.itemviews.custom_columns import make_delegate_column
from picard.ui.itemviews.custom_columns.protocols import DelegateProvider
from picard.ui.itemviews.custom_columns.sorting_adapters import NumericSortAdapter
from picard.ui.itemviews.match_quality_column import MatchQualityProvider


class _DelegateSortingWrapper(DelegateProvider):
    """Lightweight adapter that is a DelegateProvider and exposes sort.

    Wraps a `DelegateProvider` and a `SortKeyProvider` (adapter over the same
    base) so that the result is both a `DelegateProvider` (for type-checking)
    and provides evaluate/sort_key via delegation to the sorting adapter.
    """

    def __init__(self, base: DelegateProvider, sorter):
        self._base = base
        self._sorter = sorter
        # Surface parser for existing tests expecting this attribute on adapter
        if hasattr(sorter, '_parser'):
            self._parser = sorter._parser  # type: ignore[attr-defined]

    def get_delegate_class(self) -> type:
        return self._base.get_delegate_class()

    def evaluate(self, obj):  # type: ignore[override]
        return self._sorter.evaluate(obj)

    def sort_key(self, obj):  # pragma: no cover - passthrough
        return self._sorter.sort_key(obj)


def create_match_quality_column():
    """Create a match quality delegate column with proper sorting.

    Returns
    -------
    DelegateColumn
        The configured match quality column.
    """
    base = MatchQualityProvider()
    sorter = NumericSortAdapter(base)
    delegate_provider = _DelegateSortingWrapper(base, sorter)
    column = make_delegate_column(
        N_("Match"),
        '~match_quality',
        delegate_provider,
        width=57,
        sort_type=ColumnSortType.SORTKEY,
        size=QtCore.QSize(16, 16),
    )
    column.is_default = True
    return column
