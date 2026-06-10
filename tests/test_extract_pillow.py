from __future__ import annotations

from pathlib import Path

from PIL import Image

from autopalette.config import PaletteConfig
from autopalette.extract.pillow import PillowExtractor


def _make_image(tmp_path: Path) -> Path:
    img = Image.new("RGB", (128, 64))
    bands = [(10, 12, 30), (40, 30, 70), (150, 70, 60), (230, 140, 90),
             (250, 200, 120), (40, 120, 200), (60, 200, 120), (220, 60, 60)]
    px = img.load()
    for x in range(128):
        c = bands[(x * len(bands)) // 128]
        for y in range(64):
            px[x, y] = c
    p = tmp_path / "wall.png"
    img.save(p)
    return p


def test_extract_returns_weighted_samples(tmp_path):
    ext = PillowExtractor().extract(_make_image(tmp_path), PaletteConfig())
    assert ext.samples, "expected at least one sample"
    assert all(s.hex.startswith("#") and len(s.hex) == 7 for s in ext.samples)
    # weights normalised and sorted descending
    assert abs(sum(s.weight for s in ext.samples) - 1.0) < 1e-6
    assert ext.samples == tuple(sorted(ext.samples, key=lambda s: s.weight, reverse=True))
    assert 0.0 <= ext.mean_luminance <= 1.0


def test_neutral_vibrant_split(tmp_path):
    cfg = PaletteConfig()
    ext = PillowExtractor().extract(_make_image(tmp_path), cfg)
    vibrants = ext.vibrants(cfg)
    # the test image is colourful, so there must be vibrant samples
    assert vibrants
    assert all(s.oklch.C >= cfg.vibrant_chroma_min for s in vibrants)


def test_dark_image_low_mean_luminance(tmp_path):
    img = Image.new("RGB", (64, 64), (8, 8, 16))
    p = tmp_path / "dark.png"
    img.save(p)
    ext = PillowExtractor().extract(p, PaletteConfig())
    assert ext.mean_luminance < 0.1
