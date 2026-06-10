"""The base16 palette selection algorithm.

This is a faithful port of the original ``autopalette`` Python heredoc, with two
deliberate improvements:

* The module-level mutable ``currentMaximumBackgroundBrightnessThresholdIndex``
  global is replaced by explicit state on :class:`PaletteBuilder`.
* De-duplication preserves input order (``dict.fromkeys``) instead of going
  through ``set()``, so the result is *reproducible* — the original depended on
  hash-randomised set ordering for the accent roles, which made successive runs
  on the same wallpaper produce different palettes.
"""

from __future__ import annotations

import logging
import random
from typing import Callable

from . import color
from .config import PaletteConfig

log = logging.getLogger(__name__)

# base16 roles in canonical darkest-to-lightest order. base00 (the background)
# is resolved first; contrast-based selectors compare against it.
BASE16_ROLES: tuple[str, ...] = (
    "base00",  # Default Background
    "base01",  # Lighter Background (status bars)
    "base02",  # Selection Background
    "base03",  # Comments, Invisibles, Line Highlighting
    "base04",  # Dark Foreground (status bars)
    "base05",  # Default Foreground, Caret, Delimiters, Operators
    "base06",  # Light Foreground (rarely used)
    "base07",  # Light Background (rarely used)
    "base08",  # Variables, Markup Lists, Diff Deleted
    "base09",  # Integers, Booleans, Constants, Markup Link Url
    "base0A",  # Classes, Markup Bold, Search Text Background
    "base0B",  # Strings, Markup Code, Diff Inserted
    "base0C",  # Support, Regex, Escape Characters, Markup Quotes
    "base0D",  # Functions, Methods, Headings
    "base0E",  # Keywords, Storage, Selector, Diff Changed
    "base0F",  # Deprecated, Embedded Language Tags
)

# Background-style roles get a forced-dark, brightness-clamped pick; comment /
# foreground roles get the darkest unused high-contrast colour; accent roles get
# a bright high-contrast colour.
_FORCE_DARK_ROLES = frozenset({"base00", "base01", "base02", "base06", "base07"})
_DARK_HIGH_CONTRAST_ROLES = frozenset({"base03", "base04", "base05"})


class PaletteBuilder:
    """Stateful selector that assigns one colour from ``pool`` to each role."""

    def __init__(self, config: PaletteConfig, rng: random.Random) -> None:
        self.config = config
        self.rng = rng
        self.colors: dict[str, str] = {}
        # Drives both "Nth darkest background" selection and the lightness clamp,
        # advancing only when a force-dark role is filled (mirrors the original).
        self._bg_index = 0

    @property
    def background(self) -> str:
        return self.colors[BASE16_ROLES[0]]

    def _used(self) -> set[str]:
        return set(self.colors.values())

    # -- selection strategies -------------------------------------------------

    def _pick_force_dark(self, pool: list[str]) -> str | None:
        """Pick the Nth-darkest colour and clamp its lightness so backgrounds
        stay dark and get progressively lighter across successive calls."""
        viable = sorted(pool, key=color.brightness)
        thresholds = self.config.background_brightness_thresholds
        idx = self._bg_index
        if idx < len(viable) and idx < len(thresholds):
            chosen = viable[idx]
            h, l, s = color.hex_to_hls(chosen)
            clamped = (h, min(l, thresholds[idx]), s)
            self._bg_index += 1
            return color.hls_to_hex(clamped)
        return None

    def _pick_dark_high_contrast(self, pool: list[str]) -> str | None:
        """Darkest unused colour within comment..text contrast of the background."""
        bg = self.background
        viable = sorted(
            (c for c in pool if color.within_contrast(
                c, bg, self.config.min_comment_contrast, self.config.max_text_contrast)),
            key=color.brightness,
        )
        used = self._used()
        return next((c for c in viable if c not in used), None)

    def _pick_bright_high_contrast(self, pool: list[str]) -> str | None:
        """A bright colour within text contrast of the background, preferring an
        unused one but falling back to a random viable colour."""
        bg = self.background
        viable = [
            c for c in pool
            if color.within_contrast(
                c, bg, self.config.min_text_contrast, self.config.max_text_contrast)
        ]
        if not viable:
            return None
        used = self._used()
        return next((c for c in viable if c not in used), self.rng.choice(viable))

    def _selector_for(self, role: str) -> Callable[[list[str]], "str | None"]:
        if role in _FORCE_DARK_ROLES:
            return self._pick_force_dark
        if role in _DARK_HIGH_CONTRAST_ROLES:
            return self._pick_dark_high_contrast
        return self._pick_bright_high_contrast

    # -- driver ---------------------------------------------------------------

    def build(self, pool: list[str]) -> dict[str, str]:
        for role in BASE16_ROLES:
            chosen = self._selector_for(role)(pool)
            if chosen is None:
                log.warning("role %s could not satisfy its constraints; picking at random", role)
                chosen = self.rng.choice(pool)
            self.colors[role] = chosen
            log.debug("selected %s for %s", chosen, role)
        return dict(self.colors)


def generate_palette(
    colors: list[str],
    config: PaletteConfig | None = None,
    *,
    rng: random.Random | None = None,
) -> dict[str, str]:
    """Map a pool of candidate ``#rrggbb`` colours onto the 16 base16 roles.

    Order-preserving de-duplication is applied first. Raises ``ValueError`` for
    an empty pool.
    """
    config = config or PaletteConfig()
    rng = rng or random.Random()

    pool = [c.strip() for c in colors if c.strip()]
    pool = list(dict.fromkeys(pool))  # de-dupe, preserve order
    if not pool:
        raise ValueError("colour pool is empty; extractor returned no colours")

    return PaletteBuilder(config, rng).build(pool)
