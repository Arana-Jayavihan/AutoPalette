"""Pluggable wallpaper colour extractors.

Each backend turns an image into an :class:`Extraction` (weighted OKLCh samples
+ mean luminance) that the palette synthesiser maps onto base16 roles.
"""

from __future__ import annotations

from .base import ColorSample, Extraction, Extractor

AVAILABLE = ("pillow", "schemer2")


def get_extractor(name: str, *, schemer2_bin: str | None = None) -> Extractor:
    """Instantiate an extractor backend by name (``pillow`` or ``schemer2``)."""
    if name == "pillow":
        from .pillow import PillowExtractor

        return PillowExtractor()
    if name == "schemer2":
        from .schemer2 import Schemer2Extractor

        return Schemer2Extractor(binary=schemer2_bin)
    raise ValueError(f"unknown extractor {name!r} (expected 'pillow' or 'schemer2')")


__all__ = ["AVAILABLE", "ColorSample", "Extraction", "Extractor", "get_extractor"]
