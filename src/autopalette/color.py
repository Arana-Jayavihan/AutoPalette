"""Pure colour-space helpers used by the palette algorithm.

Colours are passed around as ``#rrggbb`` strings. All conversions go through the
stdlib ``colorsys`` module; brightness is the HLS *lightness* component, matching
the heuristic the original script relied on.
"""

from __future__ import annotations

import colorsys

RGB = tuple[int, int, int]
HLS = tuple[float, float, float]


def hex_to_rgb(value: str) -> RGB:
    """Parse ``#rrggbb`` (or ``rrggbb``) into a 0-255 RGB triple."""
    h = value.strip().lstrip("#")
    if len(h) != 6:
        raise ValueError(f"expected a 6-digit hex colour, got {value!r}")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rgb_to_hex(rgb: RGB) -> str:
    """Format a 0-255 RGB triple as ``#rrggbb``."""
    r, g, b = (max(0, min(255, int(round(c)))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def hex_to_hls(value: str) -> HLS:
    r, g, b = hex_to_rgb(value)
    return colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)


def hls_to_hex(hls: HLS) -> str:
    r, g, b = colorsys.hls_to_rgb(*hls)
    return rgb_to_hex((r * 255.0, g * 255.0, b * 255.0))


def brightness(value: str) -> float:
    """HLS lightness of a colour, in ``[0, 1]``."""
    return hex_to_hls(value)[1]


def contrast(color: str, background: str) -> float:
    """Signed brightness difference between ``color`` and ``background``."""
    return brightness(color) - brightness(background)


def within_contrast(color: str, background: str, minimum: float, maximum: float) -> bool:
    """True when ``color`` sits within ``[minimum, maximum]`` brightness of ``background``."""
    return minimum <= contrast(color, background) <= maximum


def rgb_distance(a: RGB, b: RGB) -> float:
    """Euclidean distance between two RGB triples (used to merge near-duplicates)."""
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5
