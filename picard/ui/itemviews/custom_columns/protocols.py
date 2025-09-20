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

"""Protocols for custom column value providers and optional sort capability."""

from __future__ import annotations

from typing import (
    Protocol,
    TypeAlias,
    runtime_checkable,
)

from picard.item import Item


@runtime_checkable
class ColumnValueProvider(Protocol):
    def evaluate(self, obj: Item) -> str:
        """Return evaluated text value for item.

        Parameters
        ----------
        obj
            The item to evaluate.

        Returns
        -------
        str
            Evaluated text value.
        """
        ...


@runtime_checkable
class SortKeyProvider(Protocol):
    def sort_key(self, obj: Item):  # pragma: no cover - optional
        """Return sort key for item.

        Parameters
        ----------
        obj
            The item to compute the sort key for.

        Returns
        -------
        Any
            Sort key.
        """
        ...


@runtime_checkable
class DelegateProvider(Protocol):
    """Protocol for columns that require custom rendering via delegates."""

    def get_delegate_class(self) -> type:
        """Return the delegate class for custom rendering.

        Returns
        -------
        type
            The delegate class (subclass of QStyledItemDelegate).
        """
        ...


@runtime_checkable
class DelegateAdapter(Protocol):
    """Protocol for adapters that wrap a `DelegateProvider`.

    An adapter implementing this protocol exposes the wrapped provider via
    the `_base` attribute and forwards value evaluation and optional sort key
    computation. This allows using adapters (e.g. sorting adapters) where a
    delegate provider is expected, while still accessing the underlying
    delegate for rendering.

    Notes
    -----
    - The `_base` must provide `get_delegate_class()`.
    - `evaluate` returns a textual value to support sorting / testing.
    - `sort_key` is optional; if implemented it provides stable custom sort.
    """

    _base: DelegateProvider

    def evaluate(self, obj: Item) -> str:  # pragma: no cover - structural typing only
        """Return evaluated text value for item."""
        ...

    def sort_key(self, obj: Item):  # pragma: no cover - optional
        """Return sort key for item, if supported."""
        ...


# Type alias for providers accepted by delegate columns / factories
DelegateColumnProvider: TypeAlias = DelegateProvider | DelegateAdapter
