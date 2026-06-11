"""Measurable palette quality scoring.

The synthesiser aims at exactly these checks, and the corpus gate uses them to
prove the ">=95% of wallpapers" target objectively instead of by eye.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import color
from .config import PaletteConfig
from .roles import (
    ACCENT_ROLES,
    BACKGROUND,
    COMMENT,
    FOREGROUND,
    RAINBOW_ROLES,
    RAMP_ROLES,
)


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    score: float  # 0..1
    detail: str
    critical: bool


@dataclass(frozen=True)
class QualityReport:
    score: float          # 0..100 weighted
    passed: bool          # all critical checks passed
    checks: tuple[Check, ...]

    def failures(self) -> list[Check]:
        return [c for c in self.checks if not c.passed]


def _ramp_lightnesses(palette: dict[str, str]) -> list[float]:
    # Perceptually-uniform OKLab L: near-black backgrounds differ subtly in WCAG
    # luminance but are evenly spaced (and visibly distinct) in OKLab.
    return [color.hex_to_oklab(palette[r]).L for r in RAMP_ROLES]


def _check_text_contrast(palette: dict[str, str], cfg: PaletteConfig) -> Check:
    bg = palette[BACKGROUND]
    # base0F (brown) is exempt from the strict text rules by convention.
    text_roles = [FOREGROUND, *RAINBOW_ROLES]
    ratios = {r: color.contrast_ratio(palette[r], bg) for r in text_roles}
    above_floor = sum(v >= cfg.text_contrast_floor for v in ratios.values())
    above_target = sum(v >= cfg.text_contrast_target for v in ratios.values())
    worst = min(ratios.items(), key=lambda kv: kv[1])
    return Check(
        name="text_contrast",
        passed=above_floor == len(ratios),  # critical: every role clears the floor
        score=above_target / len(ratios),   # scored: how many clear the AA target
        detail=f"{above_floor}/{len(ratios)} >= {cfg.text_contrast_floor} floor, "
               f"{above_target}/{len(ratios)} >= {cfg.text_contrast_target} target "
               f"(worst {worst[0]}={worst[1]:.2f})",
        critical=True,
    )


def _check_comment_contrast(palette: dict[str, str], cfg: PaletteConfig) -> Check:
    bg = palette[BACKGROUND]
    ratio = color.contrast_ratio(palette[COMMENT], bg)
    passed = ratio >= cfg.comment_contrast_min
    return Check(
        name="comment_contrast",
        passed=passed,
        score=min(1.0, ratio / cfg.comment_contrast_min),
        detail=f"base03={ratio:.2f}:1 (need {cfg.comment_contrast_min})",
        critical=False,
    )


def _check_ramp_monotonic(palette: dict[str, str]) -> Check:
    Ls = _ramp_lightnesses(palette)
    diffs = [b - a for a, b in zip(Ls, Ls[1:])]
    increasing = all(d > 0 for d in diffs)
    decreasing = all(d < 0 for d in diffs)
    monotonic = increasing or decreasing
    min_step = min(abs(d) for d in diffs)
    return Check(
        name="ramp_monotonic",
        passed=monotonic and min_step > 0.01,
        score=1.0 if monotonic else 0.0,
        detail=f"{'monotonic' if monotonic else 'NON-monotonic'} ramp, "
               f"min OKLab-L step {min_step:.3f}",
        critical=True,
    )


def _check_accent_distinct(palette: dict[str, str], cfg: PaletteConfig) -> Check:
    # Accents may reuse the wallpaper's hues (so every accent is a colour from the
    # image); what matters is that no two of the 8 collapse into one another. They
    # are judged distinct by perceptual distance (ΔE), not by hue angle, so a
    # lighter and a darker shade of the same hue both count.
    accents = [palette[r] for r in ACCENT_ROLES]
    min_de = 999.0
    too_close = 0
    for i in range(len(accents)):
        for j in range(i + 1, len(accents)):
            d = color.delta_e(accents[i], accents[j])
            min_de = min(min_de, d)
            if d < cfg.accent_min_delta_e:
                too_close += 1

    pairs = len(accents) * (len(accents) - 1) // 2
    return Check(
        name="accent_distinct",
        passed=too_close == 0,
        score=max(0.0, 1.0 - too_close / pairs),
        detail=f"{too_close} pair(s) within ΔE {cfg.accent_min_delta_e:.3f}, "
               f"min ΔE {min_de:.3f}",
        critical=True,
    )


def _check_accent_cohesion(palette: dict[str, str]) -> Check:
    accents = [color.hex_to_oklab(palette[r]) for r in ACCENT_ROLES]
    Ls = [a.L for a in accents]
    Cs = [a.C for a in accents]
    spread_L = max(Ls) - min(Ls)
    spread_C = max(Cs) - min(Cs)
    # cohesive when accents sit in a tight lightness/chroma band
    score = max(0.0, 1.0 - (spread_L / 0.35) * 0.5 - (spread_C / 0.18) * 0.5)
    return Check(
        name="accent_cohesion",
        passed=spread_L <= 0.30 and spread_C <= 0.16,
        score=min(1.0, score),
        detail=f"lightness spread {spread_L:.2f}, chroma spread {spread_C:.2f}",
        critical=False,
    )


_WEIGHTS = {
    "text_contrast": 0.35,
    "ramp_monotonic": 0.20,
    "accent_distinct": 0.25,
    "comment_contrast": 0.08,
    "accent_cohesion": 0.12,
}


def score_palette(palette: dict[str, str], config: PaletteConfig | None = None) -> QualityReport:
    cfg = config or PaletteConfig()
    checks = (
        _check_text_contrast(palette, cfg),
        _check_ramp_monotonic(palette),
        _check_accent_distinct(palette, cfg),
        _check_comment_contrast(palette, cfg),
        _check_accent_cohesion(palette),
    )
    total = sum(_WEIGHTS[c.name] * c.score for c in checks)
    passed = all(c.passed for c in checks if c.critical)
    return QualityReport(score=round(total * 100, 1), passed=passed, checks=checks)
