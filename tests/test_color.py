from __future__ import annotations

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


def test_brightness_ordering():
    assert color.brightness("#000000") == 0.0
    assert color.brightness("#ffffff") == 1.0
    assert color.brightness("#101010") < color.brightness("#a0a0a0")


def test_contrast_and_within():
    assert color.contrast("#ffffff", "#000000") == pytest.approx(1.0)
    assert color.within_contrast("#808080", "#000000", 0.3, 0.65)
    assert not color.within_contrast("#0a0a0a", "#000000", 0.3, 0.65)


def test_rgb_distance():
    assert color.rgb_distance((0, 0, 0), (0, 0, 0)) == 0
    assert color.rgb_distance((0, 0, 0), (255, 0, 0)) == pytest.approx(255.0)
