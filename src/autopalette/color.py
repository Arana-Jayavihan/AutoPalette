"""Perceptual colour engine: sRGB <-> OKLab/OKLCh, WCAG contrast, ΔE.

All palette reasoning is done in OKLab / OKLCh (Björn Ottosson's perceptually
uniform space) rather than HLS, so "brightness", "distance" and "hue" behave the
way the eye expects. Readability is judged with the WCAG contrast ratio.

Scalar helpers take/return ``#rrggbb`` strings or plain tuples; the ``*_arr``
helpers are numpy-vectorised for whole pixel arrays (shape ``(..., 3)``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

RGB = tuple[int, int, int]

# --- sRGB <-> linear -------------------------------------------------------


def _srgb_to_linear_arr(c: np.ndarray) -> np.ndarray:
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb_arr(c: np.ndarray) -> np.ndarray:
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.clip(c, 0, None) ** (1 / 2.4) - 0.055)


# --- linear sRGB <-> OKLab (Ottosson matrices) -----------------------------

_M1 = np.array([
    [0.4122214708, 0.5363325363, 0.0514459929],
    [0.2119034982, 0.6806995451, 0.1073969566],
    [0.0883024619, 0.2817188376, 0.6299787005],
])
_M2 = np.array([
    [0.2104542553, 0.7936177850, -0.0040720468],
    [1.9779984951, -2.4285922050, 0.4505937099],
    [0.0259040371, 0.7827717662, -0.8086757660],
])
_M2_INV = np.linalg.inv(_M2)
_M1_INV = np.linalg.inv(_M1)


def linear_rgb_to_oklab_arr(rgb: np.ndarray) -> np.ndarray:
    lms = np.asarray(rgb, dtype=np.float64) @ _M1.T
    lms_ = np.cbrt(lms)
    return lms_ @ _M2.T


def oklab_to_linear_rgb_arr(lab: np.ndarray) -> np.ndarray:
    lms_ = np.asarray(lab, dtype=np.float64) @ _M2_INV.T
    lms = lms_ ** 3
    return lms @ _M1_INV.T


def srgb_to_oklab_arr(rgb01: np.ndarray) -> np.ndarray:
    """sRGB in [0,1] (shape (...,3)) -> OKLab."""
    return linear_rgb_to_oklab_arr(_srgb_to_linear_arr(rgb01))


def oklab_to_srgb_arr(lab: np.ndarray) -> np.ndarray:
    """OKLab -> sRGB in [0,1], clipped to gamut."""
    return np.clip(_linear_to_srgb_arr(oklab_to_linear_rgb_arr(lab)), 0.0, 1.0)


# --- string / tuple scalar helpers -----------------------------------------


def hex_to_rgb(value: str) -> RGB:
    h = value.strip().lstrip("#")
    if len(h) != 6:
        raise ValueError(f"expected a 6-digit hex colour, got {value!r}")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rgb_to_hex(rgb) -> str:
    r, g, b = (max(0, min(255, int(round(float(c))))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def hex_to_oklab(value: str) -> "OKLCh":
    rgb01 = np.array(hex_to_rgb(value), dtype=np.float64) / 255.0
    lab = srgb_to_oklab_arr(rgb01)
    return OKLCh.from_lab(float(lab[0]), float(lab[1]), float(lab[2]))


def oklab_to_hex(L: float, a: float, b: float) -> str:
    rgb01 = oklab_to_srgb_arr(np.array([L, a, b], dtype=np.float64))
    return rgb_to_hex(tuple(rgb01 * 255.0))


def _lab_in_gamut(L: float, a: float, b: float, eps: float = 1e-3) -> bool:
    raw = _linear_to_srgb_arr(oklab_to_linear_rgb_arr(np.array([L, a, b])))
    return bool(raw.min() >= -eps and raw.max() <= 1.0 + eps)


def oklch_to_hex(L: float, C: float, h: float) -> str:
    """Convert OKLCh to a hex colour, gamut-mapping by *reducing chroma* (which
    preserves hue and lightness) rather than clipping RGB channels (which shifts
    hue). Essential so two accents placed N° apart stay N° apart on screen."""
    hr = math.radians(h)
    cos_h, sin_h = math.cos(hr), math.sin(hr)
    if not _lab_in_gamut(L, C * cos_h, C * sin_h):
        lo, hi = 0.0, C
        for _ in range(20):
            mid = (lo + hi) / 2.0
            if _lab_in_gamut(L, mid * cos_h, mid * sin_h):
                lo = mid
            else:
                hi = mid
        C = lo
    return oklab_to_hex(L, C * cos_h, C * sin_h)


# --- OKLCh value object -----------------------------------------------------


@dataclass(frozen=True)
class OKLCh:
    """A colour in OKLCh: lightness L in [0,1], chroma C >= 0, hue h in degrees."""

    L: float
    C: float
    h: float  # degrees [0, 360)

    @classmethod
    def from_lab(cls, L: float, a: float, b: float) -> "OKLCh":
        C = math.hypot(a, b)
        h = math.degrees(math.atan2(b, a)) % 360.0
        return cls(L, C, h)

    def to_lab(self) -> tuple[float, float, float]:
        hr = math.radians(self.h)
        return (self.L, self.C * math.cos(hr), self.C * math.sin(hr))

    def to_hex(self) -> str:
        return oklch_to_hex(self.L, self.C, self.h)

    def replace(self, *, L: float | None = None, C: float | None = None,
                h: float | None = None) -> "OKLCh":
        return OKLCh(
            self.L if L is None else L,
            max(0.0, self.C if C is None else C),
            (self.h if h is None else h) % 360.0,
        )


# --- WCAG contrast ----------------------------------------------------------


def relative_luminance(value: str) -> float:
    """WCAG relative luminance of a hex colour, in [0, 1]."""
    rgb01 = np.array(hex_to_rgb(value), dtype=np.float64) / 255.0
    lin = _srgb_to_linear_arr(rgb01)
    return float(0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2])


def contrast_ratio(a: str, b: str) -> float:
    """WCAG contrast ratio between two hex colours (1.0 .. 21.0)."""
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# --- perceptual distance ----------------------------------------------------


def delta_e(a: str, b: str) -> float:
    """Perceptual distance (OKLab Euclidean) between two hex colours."""
    la = hex_to_oklab(a).to_lab()
    lb = hex_to_oklab(b).to_lab()
    return math.dist(la, lb)


def hue_distance(h1: float, h2: float) -> float:
    """Smallest angular distance between two hues, in degrees [0, 180]."""
    d = abs((h1 - h2) % 360.0)
    return min(d, 360.0 - d)
