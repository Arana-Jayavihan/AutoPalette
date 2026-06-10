"""Output renderers: turn a base16 palette into nix / json / html text."""

from __future__ import annotations

from ..config import PaletteConfig
from .html import render_html
from .json_ import render_json
from .nix import render_nix

_RENDERERS = {
    "nix": render_nix,
    "json": render_json,
    "html": render_html,
}

FORMATS = tuple(_RENDERERS)


def render(palette: dict[str, str], config: PaletteConfig, fmt: str) -> str:
    """Render ``palette`` in the requested format (``nix``, ``json`` or ``html``)."""
    try:
        renderer = _RENDERERS[fmt]
    except KeyError:
        raise ValueError(f"unknown format {fmt!r} (expected one of {', '.join(FORMATS)})")
    return renderer(palette, config)
