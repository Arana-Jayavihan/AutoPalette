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


def _ensure_contrast(c: color.OKLCh, bg: str, floor: float, dark: bool) -> color.OKLCh:
    """Nudge lightness until the colour clears the contrast floor against bg."""
    step = 0.02
    for _ in range(45):
        if color.contrast_ratio(c.to_hex(), bg) >= floor:
            break
        new_L = c.L + step if dark else c.L - step
        new_L = max(0.04, min(0.98, new_L))
        if new_L == c.L:
            break
        c = c.replace(L=new_L)
    return c


def _place_accent(hue: float, chroma: float, src_L: float, cfg: PaletteConfig,
                  bg: str, dark: bool) -> str:
    """Render one accent: wallpaper hue + (clamped) wallpaper chroma, at a
    readability-biased lightness, nudged to clear the contrast floor."""
    chroma = max(cfg.accent_chroma_min,
                 min(cfg.accent_chroma_max, chroma * cfg.accent_chroma_boost))
    target_L = cfg.accent_lightness(dark)
    f = cfg.accent_lightness_faithfulness
    # Follow the source lightness only partway, and keep it inside a cohesive band
    # around the readable target so accents stay legible and don't drift down into
    # base0F's darker territory.
    L = target_L + (src_L - target_L) * f
    band = cfg.accent_lightness_band
    L = max(target_L - band, min(target_L + band, L))
    c = color.OKLCh(L, chroma, hue)
    return _ensure_contrast(c, bg, cfg.text_contrast_floor, dark).to_hex()


def _synth_gap_hue(chosen: list[float]) -> float:
    """The hue in the middle of the widest gap between already-chosen hues."""
    if not chosen:
        return 0.0
    ring = sorted(chosen)
    best_hue, best_gap = ring[0], -1.0
    for a, b in zip(ring, ring[1:] + [ring[0] + 360.0]):
        gap = b - a
        if gap > best_gap:
            best_gap, best_hue = gap, (a + gap / 2.0) % 360.0
    return best_hue


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


def _build_accents(extraction: Extraction, cfg: PaletteConfig, dark: bool,
                   bg: str) -> dict[str, str]:
    # Margin above the scored minimum so 8-bit hex quantisation can't push two
    # accents under the separation threshold.
    sep = cfg.min_accent_hue_separation + 6.0
    pool = list(_accent_sources(extraction, cfg))

    accents: dict[str, str] = {}
    chosen_hues: list[float] = []
    chosen_chromas: list[float] = []

    # base08..base0E: take the wallpaper's most prominent, well-separated hues;
    # synthesise into the widest gap once the wallpaper runs out of distinct ones.
    for role in RAINBOW_ROLES:
        src = next((s for s in pool
                    if all(color.hue_distance(s.oklch.h, h) >= sep for h in chosen_hues)),
                   None)
        if src is not None:
            pool.remove(src)
            hue, chroma, src_L = src.oklch.h, src.oklch.C, src.oklch.L
        else:
            hue = _synth_gap_hue(chosen_hues)
            # Blend in with the accents already drawn from the wallpaper.
            chroma = (sum(chosen_chromas) / len(chosen_chromas)
                      if chosen_chromas else cfg.accent_chroma(dark))
            src_L = cfg.accent_lightness(dark)
        accents[role] = _place_accent(hue, chroma, src_L, cfg, bg, dark)
        chosen_hues.append(hue)
        chosen_chromas.append(chroma)

    # base0F ("deprecated"): a muted, darker companion to the first accent's hue,
    # held only to the comment-contrast floor (exempt from the rainbow rules).
    brown_hue = chosen_hues[0]
    brown_chroma = max(cfg.accent_chroma_min,
                       min(cfg.accent_chroma_max, chosen_chromas[0] * 0.7))
    brown = color.OKLCh(cfg.accent_lightness(dark) * (0.78 if dark else 1.0),
                        brown_chroma, brown_hue)
    accents["base0F"] = _ensure_contrast(brown, bg, cfg.comment_contrast_min, dark).to_hex()

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
