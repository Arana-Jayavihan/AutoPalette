from __future__ import annotations

import random

from autopalette import color
from autopalette.config import PaletteConfig
from autopalette.extract.base import ColorSample, Extraction
from autopalette.palette import synthesize
from autopalette.quality import score_palette
from autopalette.roles import BASE16_ROLES, CANONICAL_HUE, RAMP_ROLES

# A spread of wallpaper-ish colours (dark blues + warm accents).
POOL = [
    "#0a0c14", "#101828", "#243049", "#566a8c",
    "#8f465a", "#bf7c73", "#ec8866", "#f76848",
    "#ffbe6a", "#2ecc71", "#3a7bd5",
]

# A nearly-monochrome (hard) case: shades of teal only.
MONO = ["#06231f", "#0a3b33", "#0f5a4e", "#1b8a78", "#2fae98"]


def _extraction(hexes, mean_lum=0.15):
    return Extraction(
        samples=tuple(ColorSample.from_hex(h, 1.0 / len(hexes)) for h in hexes),
        mean_luminance=mean_lum,
    )


def test_all_roles_present():
    pal = synthesize(_extraction(POOL), rng=random.Random(0))
    assert list(pal) == list(BASE16_ROLES)
    assert all(v.startswith("#") and len(v) == 7 for v in pal.values())


def test_quality_passes_for_normal_wallpaper():
    pal = synthesize(_extraction(POOL), rng=random.Random(0))
    report = score_palette(pal)
    assert report.passed, [c.detail for c in report.failures()]


def test_quality_passes_for_monochrome_wallpaper():
    # The synthesis fallback must still yield a complete, readable palette.
    pal = synthesize(_extraction(MONO), rng=random.Random(0))
    report = score_palette(pal)
    assert report.passed, [c.detail for c in report.failures()]


def test_ramp_is_monotonic_dark():
    pal = synthesize(_extraction(POOL, mean_lum=0.1), PaletteConfig(mode="dark"))
    lums = [color.relative_luminance(pal[r]) for r in RAMP_ROLES]
    assert lums == sorted(lums)
    assert lums[0] < 0.1  # base00 is dark


def test_light_mode_has_light_background():
    pal = synthesize(_extraction(POOL), PaletteConfig(mode="light"))
    lums = [color.relative_luminance(pal[r]) for r in RAMP_ROLES]
    assert lums[0] > 0.7  # base00 is light
    assert lums == sorted(lums, reverse=True)  # ramp descends


def test_auto_mode_picks_dark_for_dark_image():
    dark = synthesize(_extraction(POOL, mean_lum=0.08), PaletteConfig(mode="auto"))
    light = synthesize(_extraction(POOL, mean_lum=0.85), PaletteConfig(mode="auto"))
    assert color.relative_luminance(dark["base00"]) < 0.1
    assert color.relative_luminance(light["base00"]) > 0.7


def test_anchors_are_canonical_hues():
    pal = synthesize(_extraction(POOL), rng=random.Random(0))
    for role in ("base08", "base0B", "base0D"):
        got = color.hex_to_oklab(pal[role]).h
        assert color.hue_distance(got, CANONICAL_HUE[role]) < 12, role


def test_deterministic():
    a = synthesize(_extraction(POOL), rng=random.Random(7))
    b = synthesize(_extraction(POOL), rng=random.Random(7))
    assert a == b
