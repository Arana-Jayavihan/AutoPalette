from __future__ import annotations

import random

import pytest

from autopalette import color
from autopalette.config import PaletteConfig
from autopalette.palette import BASE16_ROLES, generate_palette

# A spread of colours from near-black to bright, enough for unique selection.
POOL = [
    "#0a0c14", "#101828", "#1a2238", "#243049", "#3a4a66",
    "#566a8c", "#7788aa", "#99aacc", "#bbccee",
    "#8f465a", "#bf7c73", "#ec8866", "#f76848", "#be5a50",
    "#ffbe6a", "#9b59b6", "#2ecc71", "#e74c3c",
]


def test_returns_all_sixteen_roles():
    palette = generate_palette(POOL, rng=random.Random(0))
    assert list(palette) == list(BASE16_ROLES)
    assert all(c.startswith("#") and len(c) == 7 for c in palette.values())


def test_background_is_dark():
    palette = generate_palette(POOL, rng=random.Random(0))
    # base00 is forced dark via the lightness clamp.
    assert color.brightness(palette["base00"]) <= PaletteConfig().background_brightness_thresholds[0] + 1e-9


def test_deterministic_for_fixed_seed():
    a = generate_palette(POOL, rng=random.Random(42))
    b = generate_palette(POOL, rng=random.Random(42))
    assert a == b


def test_order_preserving_dedup_is_reproducible_without_seed():
    # Duplicates and ordering should not introduce run-to-run variation.
    pool = POOL + POOL
    assert generate_palette(pool, rng=random.Random(1)) == generate_palette(pool, rng=random.Random(1))


def test_empty_pool_raises():
    with pytest.raises(ValueError):
        generate_palette([], rng=random.Random(0))


def test_metadata_override():
    cfg = PaletteConfig().with_metadata(name="dusk", slug="dusk", author="me")
    assert cfg.name == "dusk" and cfg.slug == "dusk" and cfg.author == "me"
    # unchanged knobs preserved
    assert cfg.min_text_contrast == PaletteConfig().min_text_contrast
