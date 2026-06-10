from __future__ import annotations

import json

from autopalette.config import PaletteConfig
from autopalette.palette import BASE16_ROLES
from autopalette.render import render

PALETTE = {role: "#001328" for role in BASE16_ROLES}
CONFIG = PaletteConfig().with_metadata(name="auto-generated", slug="auto-generated",
                                       author="Lucifer 🍃")


def test_nix_matches_expected_attrset_shape():
    out = render(PALETTE, CONFIG, "nix")
    assert out.startswith("{\n  customPalette = {\n")
    assert '    name = "auto-generated";' in out
    assert '      base00 = "#001328";' in out
    assert '      base0F = "#001328";' in out
    # closes cleanly with a trailing newline
    assert out.endswith("};\n  };\n}\n")
    # every role present exactly once
    for role in BASE16_ROLES:
        assert out.count(f"      {role} = ") == 1


def test_json_roundtrips():
    out = render(PALETTE, CONFIG, "json")
    data = json.loads(out)
    assert data["name"] == "auto-generated"
    assert data["palette"]["base08"] == "#001328"
    assert list(data["palette"]) == list(BASE16_ROLES)


def test_html_contains_swatches():
    out = render(PALETTE, CONFIG, "html")
    assert "<!DOCTYPE html>" in out
    assert "background-color: #001328;" in out
    assert out.count("color-box") == len(BASE16_ROLES) + 1  # +1 for the CSS rule
