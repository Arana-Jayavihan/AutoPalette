"""base16 role taxonomy and canonical accent hues.

Kept dependency-light (only ``color``) so both the synthesiser and the scorer can
import it without a cycle.
"""

from __future__ import annotations

from .color import hex_to_oklab

BASE16_ROLES: tuple[str, ...] = tuple(f"base0{c}" for c in "0123456789ABCDEF")

# base00-base07: the neutral background->foreground ramp (darkest..lightest).
RAMP_ROLES: tuple[str, ...] = BASE16_ROLES[:8]
# base08-base0F: the 8 accents.
ACCENT_ROLES: tuple[str, ...] = BASE16_ROLES[8:]
# base08-base0E: the 7 "rainbow" accents held to hue-spread/contrast rules.
# base0F (brown/"deprecated") is conventionally low-contrast and close in hue to
# red/orange, so it is exempt from those checks.
RAINBOW_ROLES: tuple[str, ...] = BASE16_ROLES[8:15]

BACKGROUND = "base00"
FOREGROUND = "base05"
COMMENT = "base03"

# Canonical OKLCh hue (degrees) for each accent slot, derived from reference
# colours so syntax highlighting keeps its conventional meaning.
def _hue(hex_value: str) -> float:
    return hex_to_oklab(hex_value).h


CANONICAL_HUE: dict[str, float] = {
    "base08": _hue("#ff0000"),  # red    - errors, diff-deleted, variables
    "base09": _hue("#ff8000"),  # orange - numbers, constants
    "base0A": _hue("#ffd000"),  # yellow - classes, search highlight
    "base0B": _hue("#00c000"),  # green  - strings, diff-inserted
    "base0C": _hue("#00c0c0"),  # cyan   - regex, escapes
    "base0D": _hue("#0080ff"),  # blue   - functions
    "base0E": _hue("#c000ff"),  # magenta- keywords
    "base0F": _hue("#a0522d"),  # brown  - deprecated
}

# Middle path: only these slots are *anchored* to their canonical hue. The rest
# are filled from the wallpaper's prominent hues (harmonised, but not forced).
ANCHOR_ROLES: tuple[str, ...] = ("base08", "base0B", "base0D")  # red, green, blue
FILL_ROLES: tuple[str, ...] = tuple(r for r in ACCENT_ROLES if r not in ANCHOR_ROLES)
