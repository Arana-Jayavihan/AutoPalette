"""base16 role taxonomy.

Kept dependency-light so both the synthesiser and the scorer can import it
without a cycle.
"""

from __future__ import annotations

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
