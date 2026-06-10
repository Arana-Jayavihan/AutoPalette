from __future__ import annotations

from autopalette.quality import score_palette
from autopalette.roles import BASE16_ROLES

# Tomorrow Night - a well-regarded, hand-made base16 dark scheme.
TOMORROW_NIGHT = {
    "base00": "#1d1f21", "base01": "#282a2e", "base02": "#373b41", "base03": "#969896",
    "base04": "#b4b7b4", "base05": "#c5c8c6", "base06": "#e0e0e0", "base07": "#ffffff",
    "base08": "#cc6666", "base09": "#de935f", "base0A": "#f0c674", "base0B": "#b5bd68",
    "base0C": "#8abeb7", "base0D": "#81a2be", "base0E": "#b294bb", "base0F": "#a3685a",
}

# Deliberately broken: flat ramp + every accent identical.
BROKEN = {r: "#222222" for r in BASE16_ROLES}
BROKEN.update({r: "#3a3a3a" for r in ("base08", "base09", "base0A", "base0B",
                                      "base0C", "base0D", "base0E", "base0F")})


def test_good_scheme_passes_and_scores_high():
    report = score_palette(TOMORROW_NIGHT)
    assert report.passed, [c.detail for c in report.failures()]
    assert report.score >= 85


def test_broken_scheme_fails():
    report = score_palette(BROKEN)
    assert not report.passed
    assert report.score < 50
    names = {c.name for c in report.failures()}
    assert "ramp_monotonic" in names
    assert "accent_distinct" in names


def test_report_lists_failures():
    report = score_palette(BROKEN)
    assert all(not c.passed for c in report.failures())
