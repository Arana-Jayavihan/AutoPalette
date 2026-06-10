"""Shared extraction data model.

An ``Extraction`` is the structured handoff from a colour-extraction backend to
the palette synthesiser: weighted colour samples plus the image's overall
luminance (for the auto light/dark decision). Samples carry OKLCh so the
synthesiser can split them into neutral (ramp) and vibrant (accent) pools.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from .. import color
from ..config import PaletteConfig


@dataclass(frozen=True)
class ColorSample:
    hex: str
    oklch: color.OKLCh
    weight: float  # fraction of image pixels, 0..1

    @classmethod
    def from_hex(cls, hex_value: str, weight: float = 0.0) -> "ColorSample":
        return cls(hex=hex_value, oklch=color.hex_to_oklab(hex_value), weight=weight)


@dataclass(frozen=True)
class Extraction:
    samples: tuple[ColorSample, ...]  # sorted by weight, descending
    mean_luminance: float             # weighted WCAG luminance of the image, 0..1

    def neutrals(self, cfg: PaletteConfig) -> list[ColorSample]:
        return [s for s in self.samples if s.oklch.C < cfg.neutral_chroma_max]

    def vibrants(self, cfg: PaletteConfig) -> list[ColorSample]:
        return [s for s in self.samples if s.oklch.C >= cfg.vibrant_chroma_min]

    @classmethod
    def from_hexes(cls, hexes: list[str]) -> "Extraction":
        """Build an Extraction from a bare hex list (e.g. the schemer2 backend),
        with uniform weights and luminance averaged over the colours."""
        if not hexes:
            return cls(samples=(), mean_luminance=0.0)
        w = 1.0 / len(hexes)
        samples = tuple(ColorSample.from_hex(h, w) for h in hexes)
        mean_lum = sum(color.relative_luminance(h) for h in hexes) / len(hexes)
        return cls(samples=samples, mean_luminance=mean_lum)


@runtime_checkable
class Extractor(Protocol):
    def extract(self, image: Path, cfg: PaletteConfig) -> Extraction:
        ...
