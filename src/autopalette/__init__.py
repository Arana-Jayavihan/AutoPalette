"""Generate a base16 colour palette from a wallpaper image."""

from __future__ import annotations

from .config import PaletteConfig
from .palette import BASE16_ROLES, generate_palette

__version__ = "0.1.0"
__all__ = ["PaletteConfig", "BASE16_ROLES", "generate_palette", "__version__"]
