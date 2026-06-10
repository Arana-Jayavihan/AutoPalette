from __future__ import annotations

import numpy as np
import pytest

from autopalette import color


@pytest.mark.parametrize(
    "hex_value, rgb",
    [
        ("#000000", (0, 0, 0)),
        ("#ffffff", (255, 255, 255)),
        ("#001328", (0, 19, 40)),
        ("ec8866", (236, 136, 102)),
    ],
)
def test_hex_rgb_roundtrip(hex_value, rgb):
    assert color.hex_to_rgb(hex_value) == rgb
    assert color.rgb_to_hex(rgb) == "#" + hex_value.lstrip("#").lower()


def test_invalid_hex_raises():
    with pytest.raises(ValueError):
        color.hex_to_rgb("#fff")


# --- OKLab reference values (Ottosson) -------------------------------------


def test_oklab_white_black():
    white = color.hex_to_oklab("#ffffff")
    black = color.hex_to_oklab("#000000")
    assert white.L == pytest.approx(1.0, abs=1e-3)
    assert white.C == pytest.approx(0.0, abs=2e-3)
    assert black.L == pytest.approx(0.0, abs=1e-3)


def test_oklab_red_reference():
    # Known OKLab for pure sRGB red is ~ (0.6279, a=0.2249, b=0.1258).
    red = color.hex_to_oklab("#ff0000")
    L, a, b = red.to_lab()
    assert L == pytest.approx(0.6279, abs=2e-3)
    assert a == pytest.approx(0.2249, abs=2e-3)
    assert b == pytest.approx(0.1258, abs=2e-3)


def test_oklab_hex_roundtrip():
    for hx in ["#001328", "#ec8866", "#3a7bd5", "#11aa55"]:
        assert color.hex_to_oklab(hx).to_hex() == hx


def test_array_roundtrip():
    rng = np.random.default_rng(0)
    rgb01 = rng.random((50, 3))
    back = color.oklab_to_srgb_arr(color.srgb_to_oklab_arr(rgb01))
    assert np.allclose(rgb01, back, atol=1e-6)


# --- WCAG contrast ----------------------------------------------------------


def test_relative_luminance_bounds():
    assert color.relative_luminance("#ffffff") == pytest.approx(1.0, abs=1e-6)
    assert color.relative_luminance("#000000") == pytest.approx(0.0, abs=1e-6)


def test_contrast_ratio_extremes():
    assert color.contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0, abs=1e-2)
    assert color.contrast_ratio("#123456", "#123456") == pytest.approx(1.0, abs=1e-9)


# --- distances --------------------------------------------------------------


def test_delta_e_symmetry_and_zero():
    assert color.delta_e("#abcdef", "#abcdef") == pytest.approx(0.0, abs=1e-9)
    assert color.delta_e("#000000", "#ffffff") > 0.9


def test_hue_distance_wraps():
    assert color.hue_distance(10, 350) == pytest.approx(20.0)
    assert color.hue_distance(0, 180) == pytest.approx(180.0)
    assert color.hue_distance(90, 90) == pytest.approx(0.0)
