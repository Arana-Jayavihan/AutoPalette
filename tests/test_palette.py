from __future__ import annotations

import random

from autopalette import color
from autopalette.config import PaletteConfig
from autopalette.extract.base import ColorSample, Extraction
from autopalette.palette import synthesize
from autopalette.quality import score_palette
from autopalette.roles import BASE16_ROLES, RAINBOW_ROLES, RAMP_ROLES

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


def _mean_accent_chroma(pal):
    return sum(color.hex_to_oklab(pal[r]).C for r in RAINBOW_ROLES) / len(RAINBOW_ROLES)


def test_accents_follow_wallpaper_hue():
    # A teal-only wallpaper should yield a teal-leaning dominant accent rather
    # than a forced canonical red: at least one accent sits near the source hue.
    pal = synthesize(_extraction(MONO), rng=random.Random(0))
    teal = color.hex_to_oklab("#1b8a78").h
    hues = [color.hex_to_oklab(pal[r]).h for r in RAINBOW_ROLES]
    assert any(color.hue_distance(h, teal) < 25 for h in hues), hues


def test_muted_wallpaper_yields_muted_accents():
    # The core fidelity property: accent saturation tracks the wallpaper's, so a
    # near-greyscale image does not produce a vivid rainbow.
    muted = ["#403e3c", "#5a5853", "#6f6c66", "#48504a", "#574e44", "#62605a"]
    vivid = ["#ff3030", "#30c030", "#3060ff", "#ffd000", "#d000ff", "#00d0d0"]
    muted_pal = synthesize(_extraction(muted), rng=random.Random(0))
    vivid_pal = synthesize(_extraction(vivid), rng=random.Random(0))
    assert _mean_accent_chroma(muted_pal) < _mean_accent_chroma(vivid_pal)


def test_deterministic():
    a = synthesize(_extraction(POOL), rng=random.Random(7))
    b = synthesize(_extraction(POOL), rng=random.Random(7))
    assert a == b
