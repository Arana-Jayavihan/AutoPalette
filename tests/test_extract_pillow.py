from __future__ import annotations

from pathlib import Path

from PIL import Image

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


def test_extract_returns_hex_colours(tmp_path):
    colours = PillowExtractor().extract(_make_image(tmp_path), count=16, threshold=40)
    assert colours, "expected at least one colour"
    assert all(c.startswith("#") and len(c) == 7 for c in colours)
    assert len(colours) <= 16


def test_threshold_merges_similar(tmp_path):
    img = _make_image(tmp_path)
    loose = PillowExtractor().extract(img, count=64, threshold=10)
    tight = PillowExtractor().extract(img, count=64, threshold=120)
    # A larger merge threshold yields fewer (or equal) distinct colours.
    assert len(tight) <= len(loose)
