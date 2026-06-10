"""Tunable configuration for palette generation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PaletteConfig:
    """Knobs controlling the base16 selection algorithm and output metadata.

    The defaults reproduce the behaviour of the original ``autopalette`` shell
    script. ``background_brightness_thresholds`` clamps the lightness of the
    progressively-lighter background roles (base00, base01, base02, base06,
    base07); the contrast bounds gate which colours may be picked as comment /
    foreground / accent roles relative to the chosen background (base00).
    """

    background_brightness_thresholds: tuple[float, ...] = (
        0.08,
        0.15,
        0.2,
        0.25,
        0.3,
        0.4,
        0.45,
    )
    min_comment_contrast: float = 0.3
    min_text_contrast: float = 0.43
    max_text_contrast: float = 0.65

    # Output metadata (mirrors nix-colors' colorScheme schema).
    name: str = "auto-generated"
    slug: str = "auto-generated"
    author: str = "Lucifer 🍃"

    def with_metadata(self, *, name: str | None = None, slug: str | None = None,
                      author: str | None = None) -> "PaletteConfig":
        """Return a copy with metadata overridden where provided."""
        return PaletteConfig(
            background_brightness_thresholds=self.background_brightness_thresholds,
            min_comment_contrast=self.min_comment_contrast,
            min_text_contrast=self.min_text_contrast,
            max_text_contrast=self.max_text_contrast,
            name=name if name is not None else self.name,
            slug=slug if slug is not None else self.slug,
            author=author if author is not None else self.author,
        )
