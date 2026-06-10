"""Two-stage, synthesis-based base16 generation.

Instead of filtering an extracted pool and hoping it contains colours that fit
rigid bands, the palette is *constructed* so it is always complete and readable:

* Stage A - a derived neutral luminance ramp (base00..base07), tinted by the
  wallpaper's dominant hue. Always monotonic and readable; independent of whether
  the pool happens to contain good greys.
* Stage B - 8 hue-slotted accents (base08..base0F). The middle path: base08/0B/0D
  (red/green/blue) are anchored to canonical hues so syntax highlighting keeps
  its meaning; the rest are filled from the wallpaper's prominent hues, falling
  back to gap-filling synthesis. Every accent is harmonised to a consistent
  lightness/chroma and nudged until it clears the contrast floor.

The mode (dark/light) is chosen from the image's mean luminance when ``auto``.
"""

from __future__ import annotations

import random

from . import color
from .config import PaletteConfig
from .extract.base import Extraction
from .roles import (
    ACCENT_ROLES,
    ANCHOR_ROLES,
    BASE16_ROLES,
    CANONICAL_HUE,
    RAMP_ROLES,
)

# Eased ramp positions (0..1) for base00..base07: backgrounds cluster near the
# dark end, foregrounds near the light end, like hand-made base16 schemes.
# base03 (comments) is kept high enough to clear the comment contrast floor.
_RAMP_T = (0.00, 0.05, 0.11, 0.50, 0.66, 0.80, 0.90, 1.00)

# base0F (brown / deprecated): a darker, muted variant rather than a rainbow hue.
_BROWN_HUE_ROLE = "base09"  # follow the orange slot's neighbourhood


def _decide_dark(extraction: Extraction, cfg: PaletteConfig) -> bool:
    if cfg.mode == "dark":
        return True
    if cfg.mode == "light":
        return False
    return extraction.mean_luminance < cfg.auto_luminance_split


def _dominant_hue(extraction: Extraction, cfg: PaletteConfig) -> float | None:
    vibrants = extraction.vibrants(cfg)
    return vibrants[0].oklch.h if vibrants else None


def _build_ramp(extraction: Extraction, cfg: PaletteConfig, dark: bool) -> dict[str, str]:
    if dark:
        lo, hi = cfg.dark_bg_lightness, cfg.dark_fg_lightness
    else:
        lo, hi = cfg.light_bg_lightness, cfg.light_fg_lightness  # lo > hi (descending)

    hue = _dominant_hue(extraction, cfg)
    tint_c = cfg.neutral_tint_chroma if hue is not None else 0.0
    hue = hue or 0.0

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


def _harmonise(hue: float, cfg: PaletteConfig, bg: str, dark: bool) -> str:
    """Place a hue at the harmonised accent lightness/chroma, then ensure contrast."""
    c = color.OKLCh(cfg.accent_lightness(dark), cfg.accent_chroma(dark), hue)
    return _ensure_contrast(c, bg, cfg.text_contrast_floor, dark).to_hex()


def _pick_fill_hue(candidates: list[float], chosen: list[float],
                   min_sep: float) -> float:
    """Prefer a wallpaper hue far enough from already-chosen accents; otherwise
    synthesise the hue that maximises separation (largest gap on the wheel)."""
    for h in candidates:
        if all(color.hue_distance(h, c) >= min_sep for c in chosen):
            candidates.remove(h)
            return h
    # Synthesis fallback: hue in the middle of the widest gap between chosen hues.
    if not chosen:
        return 0.0
    ring = sorted(chosen)
    best_hue, best_gap = ring[0], -1.0
    for a, b in zip(ring, ring[1:] + [ring[0] + 360.0]):
        gap = b - a
        if gap > best_gap:
            best_gap, best_hue = gap, (a + gap / 2.0) % 360.0
    return best_hue


def _build_accents(extraction: Extraction, cfg: PaletteConfig, dark: bool,
                   bg: str) -> dict[str, str]:
    accents: dict[str, str] = {}
    chosen_hues: list[float] = []

    # 1. Anchors: red / green / blue forced to canonical hues.
    for role in ANCHOR_ROLES:
        hue = CANONICAL_HUE[role]
        accents[role] = _harmonise(hue, cfg, bg, dark)
        chosen_hues.append(hue)

    # 2. Fill slots from the wallpaper's prominent vibrant hues (most weighted
    #    first), synthesising into gaps when the wallpaper runs out. Build with a
    #    margin above the scored minimum so 8-bit hex quantisation can't push two
    #    accents under the separation threshold.
    sep = cfg.min_accent_hue_separation + 6.0
    vibrant_hues = [s.oklch.h for s in extraction.vibrants(cfg)]
    fill_roles = ("base09", "base0A", "base0C", "base0E")  # orange/yellow/cyan/magenta
    for role in fill_roles:
        hue = _pick_fill_hue(vibrant_hues, chosen_hues, sep)
        accents[role] = _harmonise(hue, cfg, bg, dark)
        chosen_hues.append(hue)

    # 3. base0F: a muted brown near the orange neighbourhood (exempt from rules).
    brown_hue = color.hex_to_oklab(accents[_BROWN_HUE_ROLE]).h
    brown = color.OKLCh(
        cfg.accent_lightness(dark) * (0.78 if dark else 1.0),
        cfg.accent_chroma(dark) * 0.7,
        brown_hue,
    )
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
