"""Generate a base16 colour palette from a wallpaper image."""

from __future__ import annotations

from .config import PaletteConfig
from .palette import synthesize
from .quality import score_palette
from .roles import BASE16_ROLES

__version__ = "0.2.0"
__all__ = ["PaletteConfig", "BASE16_ROLES", "synthesize", "score_palette", "__version__"]
