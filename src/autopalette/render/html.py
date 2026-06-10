"""Render a base16 palette as a standalone HTML swatch preview."""

from __future__ import annotations

from ..config import PaletteConfig
from ..palette import BASE16_ROLES

_PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Base16 Color Palette</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            padding: 20px;
            background-color: #f0f0f0;
            text-align: center;
        }}
        .palette-info {{ margin-bottom: 20px; }}
        .palette-info h1 {{ margin: 0; font-size: 24px; }}
        .palette-info p {{ margin: 5px 0 0; font-size: 18px; }}
        .container {{ display: flex; width: 100%; }}
        .color-grid {{
            position: relative;
            width: 100%;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            grid-gap: 10px;
            justify-items: center;
        }}
        .color-box {{
            width: 200px;
            height: 200px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.7);
        }}
    </style>
</head>
<body>
    <div class="palette-info">
        <h1>Wallpaper Based Auto Generated Color Palette</h1>
        <p>Author: {author}</p>
    </div>
    <div class="container">
        <div class="color-grid">
{boxes}
        </div>
    </div>
</body>
</html>
"""

_BOX = (
    '            <div class="color-box" style="background-color: {hex};">'
    "{role}<br>{hex}</div>"
)


def render_html(palette: dict[str, str], config: PaletteConfig) -> str:
    boxes = "\n".join(_BOX.format(role=role, hex=palette[role]) for role in BASE16_ROLES)
    return _PAGE.format(author=config.author, boxes=boxes)
