"""Tunable configuration shared by the synthesiser and the quality scorer.

Keeping a single source of truth means the generator aims at exactly what the
scorer measures: contrast floors, accent harmonisation targets, hue spread and
the neutral-ramp endpoints. All lightness/chroma values are in OKLab/OKLCh.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class PaletteConfig:
    # --- theme mode --------------------------------------------------------
    mode: str = "auto"  # "dark" | "light" | "auto"
    # Mean-luminance split for auto mode, with hysteresis handled at the call site.
    auto_luminance_split: float = 0.5

    # --- readability (WCAG contrast vs base00) -----------------------------
    text_contrast_floor: float = 3.0    # critical: base05 + rainbow accents must clear this
    text_contrast_target: float = 4.5   # scored: reward clearing AA normal-text
    comment_contrast_min: float = 3.0   # base03 (comments must be readable)

    # --- neutral ramp endpoints (OKLab L) ----------------------------------
    dark_bg_lightness: float = 0.15
    dark_fg_lightness: float = 0.90
    light_bg_lightness: float = 0.95
    light_fg_lightness: float = 0.25
    # The ramp is tinted by the wallpaper's overall colour cast: tint chroma is
    # the image's (chroma-weighted) mean chroma scaled by ``neutral_tint_scale``
    # and capped at ``neutral_tint_max`` so backgrounds stay readable. A truly
    # greyscale wallpaper therefore yields a grey ramp (faithfully), while a
    # colourful one gets a clearly tinted one.
    neutral_tint_scale: float = 1.0
    neutral_tint_max: float = 0.04

    # --- accents (OKLCh) ---------------------------------------------------
    # Accents follow the wallpaper: their *hue* and *chroma* come from the
    # image's prominent colours, so a muted wallpaper yields muted accents and a
    # vivid one yields vivid accents. Lightness is blended toward a readable
    # target (``accent_lightness_*``) by ``accent_lightness_faithfulness`` (0 =
    # pin to the readable target, 1 = follow the source colour), then nudged to
    # clear the contrast floor. ``accent_chroma_*`` is only the fallback chroma
    # for hues that have to be *synthesised* (when the wallpaper runs out of
    # well-separated colours).
    accent_lightness_dark: float = 0.74
    accent_chroma_dark: float = 0.14
    accent_lightness_light: float = 0.52
    accent_chroma_light: float = 0.15
    accent_lightness_faithfulness: float = 0.3
    accent_lightness_band: float = 0.12  # max +/- drift from the readable target
    accent_chroma_min: float = 0.05   # visibility floor: keep accents distinct
    accent_chroma_max: float = 0.18   # ceiling: avoid out-of-gamut oversaturation
    accent_chroma_boost: float = 1.0  # multiplier applied to source chroma
    min_accent_hue_separation: float = 20.0  # degrees; below this two accents "collapse"

    # --- extraction --------------------------------------------------------
    cluster_count: int = 16          # k-means clusters
    merge_delta_e: float = 0.05      # OKLab ΔE below which clusters are merged
    neutral_chroma_max: float = 0.045  # OKLCh C below this == neutral (ramp pool)
    vibrant_chroma_min: float = 0.045  # at/above this == vibrant (accent pool)

    # --- metadata ----------------------------------------------------------
    name: str = "auto-generated"
    slug: str = "auto-generated"
    author: str = "Lucifer 🍃"

    def with_metadata(self, *, name: str | None = None, slug: str | None = None,
                      author: str | None = None) -> "PaletteConfig":
        return replace(
            self,
            name=name if name is not None else self.name,
            slug=slug if slug is not None else self.slug,
            author=author if author is not None else self.author,
        )

    # convenience: mode-specific accent targets
    def accent_lightness(self, dark: bool) -> float:
        return self.accent_lightness_dark if dark else self.accent_lightness_light

    def accent_chroma(self, dark: bool) -> float:
        return self.accent_chroma_dark if dark else self.accent_chroma_light
