"""Render a base16 palette as a nix ``customPalette`` attrset.

The output is byte-compatible with the file the original script wrote to
``config/home/files/autopalette/custom.nix`` so it can be imported by
nix-colors' ``colorScheme`` without any consumer changes.
"""

from __future__ import annotations

from ..config import PaletteConfig
from ..palette import BASE16_ROLES


def render_nix(palette: dict[str, str], config: PaletteConfig) -> str:
    lines = [
        "{",
        "  customPalette = {",
        f'    name = "{config.name}";',
        f'    slug = "{config.slug}";',
        f'    author = "{config.author}";',
        "    palette = {",
    ]
    lines += [f'      {role} = "{palette[role]}";' for role in BASE16_ROLES]
    lines += [
        "    };",
        "  };",
        "}",
        "",
    ]
    return "\n".join(lines)
