"""Render a base16 palette as JSON."""

from __future__ import annotations

import json

from ..config import PaletteConfig
from ..palette import BASE16_ROLES


def render_json(palette: dict[str, str], config: PaletteConfig) -> str:
    payload = {
        "name": config.name,
        "slug": config.slug,
        "author": config.author,
        "palette": {role: palette[role] for role in BASE16_ROLES},
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
