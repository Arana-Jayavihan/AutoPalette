"""Pluggable wallpaper colour extractors.

Each backend turns an image into a flat list of ``#rrggbb`` candidate colours
that the palette algorithm then maps onto base16 roles.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class Extractor(Protocol):
    """A colour extractor backend."""

    def extract(self, image: Path, *, count: int, threshold: int) -> list[str]:
        """Return up to ``count`` dominant ``#rrggbb`` colours from ``image``.

        ``threshold`` controls how aggressively near-duplicate colours are
        merged; its exact meaning is backend-specific.
        """
        ...


def get_extractor(name: str, *, schemer2_bin: str | None = None) -> Extractor:
    """Instantiate an extractor backend by name (``pillow`` or ``schemer2``)."""
    if name == "pillow":
        from .pillow import PillowExtractor

        return PillowExtractor()
    if name == "schemer2":
        from .schemer2 import Schemer2Extractor

        return Schemer2Extractor(binary=schemer2_bin)
    raise ValueError(f"unknown extractor {name!r} (expected 'pillow' or 'schemer2')")


AVAILABLE = ("pillow", "schemer2")
