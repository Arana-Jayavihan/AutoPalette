"""Default extractor: Pillow decode + scikit-learn k-means in OKLab.

Clusters image pixels in perceptually-uniform OKLab space, then merges clusters
closer than an adaptive ΔE so the candidate set spans genuinely distinct
colours. Cluster weights (pixel coverage) drive both the mean-luminance estimate
and the prominence ordering the synthesiser relies on. No external binaries and
no exiftool — Pillow handles decoding and sizing.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

from .. import color
from ..config import PaletteConfig
from .base import ColorSample, Extraction

# Working resolution: dominant-colour structure is stable far below full res.
_MAX_DIMENSION = 256


class PillowExtractor:
    def extract(self, image: Path, cfg: PaletteConfig) -> Extraction:
        with Image.open(image) as img:
            img = img.convert("RGB")
            img.thumbnail((_MAX_DIMENSION, _MAX_DIMENSION))
            pixels = np.asarray(img, dtype=np.float64).reshape(-1, 3) / 255.0

        # Cluster in OKLab (perceptually uniform) rather than raw RGB.
        lab = color.srgb_to_oklab_arr(pixels)
        k = min(cfg.cluster_count, len(np.unique(lab, axis=0)))
        if k < 1:
            return Extraction(samples=(), mean_luminance=0.0)

        km = KMeans(n_clusters=k, n_init=4, random_state=0)
        labels = km.fit_predict(lab)
        centroids_lab = km.cluster_centers_
        weights = np.bincount(labels, minlength=k).astype(np.float64)
        weights /= weights.sum()

        centroids_rgb = color.oklab_to_srgb_arr(centroids_lab)
        samples = [
            ColorSample.from_hex(color.rgb_to_hex(tuple(rgb * 255.0)), float(w))
            for rgb, w in zip(centroids_rgb, weights)
        ]
        samples = _merge_similar(samples, cfg.merge_delta_e)
        samples.sort(key=lambda s: s.weight, reverse=True)

        mean_lum = float(sum(color.relative_luminance(s.hex) * s.weight for s in samples))
        return Extraction(samples=tuple(samples), mean_luminance=mean_lum)


def _merge_similar(samples: list[ColorSample], delta_e: float) -> list[ColorSample]:
    """Greedily fold samples within ΔE of a heavier kept sample, accumulating
    their weight onto the kept one."""
    kept: list[ColorSample] = []
    for s in sorted(samples, key=lambda s: s.weight, reverse=True):
        match = next((k for k in kept if color.delta_e(s.hex, k.hex) < delta_e), None)
        if match is None:
            kept.append(s)
        else:
            idx = kept.index(match)
            kept[idx] = ColorSample(match.hex, match.oklch, match.weight + s.weight)
    return kept
