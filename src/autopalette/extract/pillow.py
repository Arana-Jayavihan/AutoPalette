"""Default, self-contained extractor built on Pillow.

Quantises the image with median-cut, ranks the resulting palette by pixel
frequency, then merges colours closer than ``threshold`` in RGB space so the
pool spans a range of distinct hues rather than many near-identical shades.
Unlike the original pipeline this needs no external binaries (no ``schemer2``)
and no ``exiftool`` — Pillow handles decoding and sizing.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from .. import color

# Cap working resolution: dominant-colour results are stable well below full
# resolution and this keeps quantisation fast on large wallpapers.
_MAX_DIMENSION = 512
# Quantise to a generous palette so frequency ranking and de-duplication have
# enough material to produce a varied 16-colour pool.
_QUANTIZE_COLORS = 64


class PillowExtractor:
    def extract(self, image: Path, *, count: int = 16, threshold: int = 70) -> list[str]:
        with Image.open(image) as img:
            img = img.convert("RGB")
            img.thumbnail((_MAX_DIMENSION, _MAX_DIMENSION))
            quantized = img.quantize(colors=_QUANTIZE_COLORS, method=Image.Quantize.MEDIANCUT)

        palette = quantized.getpalette() or []
        # getcolors -> list of (pixel_count, palette_index); most frequent first.
        counts = sorted(quantized.getcolors() or [], key=lambda c: c[0], reverse=True)

        ranked: list[color.RGB] = []
        for _, index in counts:
            base = index * 3
            rgb = (palette[base], palette[base + 1], palette[base + 2])
            ranked.append(rgb)

        merged = self._merge_similar(ranked, threshold)
        return [color.rgb_to_hex(rgb) for rgb in merged[:count]]

    @staticmethod
    def _merge_similar(colors: list[color.RGB], threshold: int) -> list[color.RGB]:
        """Drop colours within ``threshold`` RGB distance of an already-kept one,
        preserving frequency order."""
        kept: list[color.RGB] = []
        for rgb in colors:
            if all(color.rgb_distance(rgb, k) >= threshold for k in kept):
                kept.append(rgb)
        return kept
