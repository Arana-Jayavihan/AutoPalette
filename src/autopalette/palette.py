"""Two-stage, wallpaper-faithful base16 generation.

Instead of filtering an extracted pool and hoping it contains colours that fit
rigid bands, the palette is *constructed* from the wallpaper so it both resembles
the image and stays complete and readable:

* Stage A - a neutral luminance ramp (base00..base07) tinted by the wallpaper's
  overall colour cast. Always monotonic; a greyscale wallpaper gives a grey ramp,
  a colourful one a clearly tinted ramp.
* Stage B - 8 accents (base08..base0F) drawn from the wallpaper's prominent
  colours. Their *hue* and *chroma* follow the image (so muted wallpapers yield
  muted accents and vivid ones yield vivid accents); when the wallpaper runs out
  of well-separated hues the remaining slots are synthesised to fill the widest
  gaps on the wheel. Lightness is blended toward a readable target and nudged
  until it clears the contrast floor. No hue is forced to a canonical value, so
  the accents reflect what is actually in the picture.

The mode (dark/light) is chosen from the image's mean luminance when ``auto``.
"""

from __future__ import annotations

import math
import random

from . import color
from .config import PaletteConfig
from .extract.base import Extraction
from .roles import (
    ACCENT_ROLES,
    BASE16_ROLES,
    RAINBOW_ROLES,
    RAMP_ROLES,
)

# Eased ramp positions (0..1) for base00..base07: backgrounds cluster near the
# dark end, foregrounds near the light end, like hand-made base16 schemes.
# base03 (comments) is kept high enough to clear the comment contrast floor.
_RAMP_T = (0.00, 0.05, 0.11, 0.50, 0.66, 0.80, 0.90, 1.00)


def _decide_dark(extraction: Extraction, cfg: PaletteConfig) -> bool:
    if cfg.mode == "dark":
        return True
    if cfg.mode == "light":
        return False
    return extraction.mean_luminance < cfg.auto_luminance_split


def _color_cast(extraction: Extraction) -> tuple[float, float]:
    """The wallpaper's overall colour cast as ``(hue, chroma)``.

    A pixel-coverage-weighted vector mean of every sample in OKLab's a/b plane.
    The resultant *hue* is the dominant tint; its *magnitude* says how colourful
    (and how hue-coherent) the image is, so it cancels toward grey for neutral or
    chromatically-balanced wallpapers."""
    x = y = w = 0.0
    for s in extraction.samples:
        hr = math.radians(s.oklch.h)
        x += s.weight * s.oklch.C * math.cos(hr)
        y += s.weight * s.oklch.C * math.sin(hr)
        w += s.weight
    if w == 0.0:
        return 0.0, 0.0
    a, b = x / w, y / w
    return math.degrees(math.atan2(b, a)) % 360.0, math.hypot(a, b)


def _build_ramp(extraction: Extraction, cfg: PaletteConfig, dark: bool) -> dict[str, str]:
    if dark:
        lo, hi = cfg.dark_bg_lightness, cfg.dark_fg_lightness
    else:
        lo, hi = cfg.light_bg_lightness, cfg.light_fg_lightness  # lo > hi (descending)

    hue, cast_chroma = _color_cast(extraction)
    tint_c = min(cast_chroma * cfg.neutral_tint_scale, cfg.neutral_tint_max)

    ramp: dict[str, str] = {}
    for role, t in zip(RAMP_ROLES, _RAMP_T):
        L = lo + (hi - lo) * t
        ramp[role] = color.OKLCh(L, tint_c, hue).to_hex()
    return ramp


def _finalize(c: color.OKLCh, bg: str, placed: list[str], floor: float,
              min_de: float, dark: bool) -> color.OKLCh:
    """Nudge lightness until the colour both clears the contrast floor against bg
    *and* is perceptually distinct (>= min_de OKLab) from every already-placed
    accent. Pushing toward the foreground end raises contrast and separates
    same-hue shades at once, so a single monotonic walk satisfies both."""
    step = 0.025
    for _ in range(60):
        hexv = c.to_hex()
        if (color.contrast_ratio(hexv, bg) >= floor
                and all(color.delta_e(hexv, p) >= min_de for p in placed)):
            break
        new_L = c.L + step if dark else c.L - step
        new_L = max(0.04, min(0.98, new_L))
        if new_L == c.L:
            break
        c = c.replace(L=new_L)
    return c


def _clamp_chroma(chroma: float, cfg: PaletteConfig) -> float:
    return max(cfg.accent_chroma_min, min(cfg.accent_chroma_max, chroma * cfg.accent_chroma_boost))


def _accent_sources(extraction: Extraction, cfg: PaletteConfig):
    """Prominent wallpaper colours to draw accents from, most prominent first.

    Prefers the vibrant pool; if the wallpaper has no vibrant colours, falls back
    to whatever samples carry the most colour (weight x chroma) so even a near
    -greyscale image yields tinted - rather than dead - accents."""
    vibrants = extraction.vibrants(cfg)
    if vibrants:
        return vibrants
    return sorted(extraction.samples,
                  key=lambda s: s.weight * s.oklch.C, reverse=True)


def _distinct_sources(extraction: Extraction, cfg: PaletteConfig, sep: float,
                      limit: int) -> list[color.OKLCh]:
    """The wallpaper's distinct accent colours: prominent hues at least ``sep``
    apart, most prominent first (so we capture the image's full hue variety
    before reusing any)."""
    chosen: list[color.OKLCh] = []
    for s in _accent_sources(extraction, cfg):
        if all(color.hue_distance(s.oklch.h, c.h) >= sep for c in chosen):
            chosen.append(s.oklch)
            if len(chosen) >= limit:
                break
    return chosen


def _build_accents(extraction: Extraction, cfg: PaletteConfig, dark: bool,
                   bg: str) -> dict[str, str]:
    # Margin above the scored separation so 8-bit hex quantisation can't merge
    # two colours we treated as distinct sources.
    sep = cfg.min_accent_hue_separation + 6.0
    sources = _distinct_sources(extraction, cfg, sep, len(RAINBOW_ROLES))
    if not sources:  # wholly achromatic image: tint from the overall colour cast
        cast_hue, _ = _color_cast(extraction)
        sources = [color.OKLCh(cfg.accent_lightness(dark), cfg.accent_chroma_min, cast_hue)]

    target = cfg.accent_lightness(dark)
    band = cfg.accent_lightness_band
    f = cfg.accent_lightness_faithfulness
    # Lightness offsets for the 2nd, 3rd, ... reuse of a hue, kept within the band
    # so a wallpaper with few colours yields distinct *shades* of its own colours.
    shade_offsets = (band, -band, band * 0.5, -band * 0.5, band * 0.75, -band * 0.75)

    accents: dict[str, str] = {}
    placed: list[str] = []
    used: dict[int, int] = {}

    # base08..base0E: every accent is one of the wallpaper's colours. Once the
    # distinct hues are spent we cycle back through them as lighter/darker shades
    # rather than inventing hues the image doesn't contain.
    for slot, role in enumerate(RAINBOW_ROLES):
        si = slot % len(sources)
        src = sources[si]
        rep = used.get(si, 0)
        used[si] = rep + 1
        if rep == 0:  # first use: the wallpaper colour at a readable lightness
            L = target + (src.L - target) * f
        else:         # a reuse: the same hue/chroma at a distinct shade
            L = target + shade_offsets[(rep - 1) % len(shade_offsets)]
        L = max(target - band, min(target + band, L))
        c = _finalize(color.OKLCh(L, _clamp_chroma(src.C, cfg), src.h),
                      bg, placed, cfg.text_contrast_floor, cfg.accent_min_delta_e, dark)
        accents[role] = c.to_hex()
        placed.append(c.to_hex())

    # base0F ("deprecated"): a muted, darker companion of the dominant hue, held
    # only to the comment-contrast floor (still distinct from the others).
    dom = sources[0]
    brown = color.OKLCh(target * (0.78 if dark else 1.0),
                        _clamp_chroma(dom.C * 0.7, cfg), dom.h)
    brown = _finalize(brown, bg, placed, cfg.comment_contrast_min,
                      cfg.accent_min_delta_e, dark)
    accents["base0F"] = brown.to_hex()

    return accents


def synthesize(extraction: Extraction, config: PaletteConfig | None = None,
               *, rng: random.Random | None = None) -> dict[str, str]:
    """Construct a complete, readable base16 palette from an extraction."""
    cfg = config or PaletteConfig()
    dark = _decide_dark(extraction, cfg)
    ramp = _build_ramp(extraction, cfg, dark)
    accents = _build_accents(extraction, cfg, dark, ramp["base00"])
    palette = {**ramp, **accents}
    return {role: palette[role] for role in BASE16_ROLES}


__all__ = ["synthesize", "BASE16_ROLES", "ACCENT_ROLES"]
