"""Opt-in extractor that shells out to the ``schemer2`` Go binary.

Reproduces the original pipeline's colour extraction, then adapts the bare hex
list into an :class:`Extraction` so it flows through the same OKLab synthesiser
(and benefits from the harmonisation). The binary is located via (in order) an
explicit path, ``$AUTOPALETTE_SCHEMER2``, or ``$PATH``; the package never
hard-depends on it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from ..config import PaletteConfig
from .base import Extraction


class Schemer2Extractor:
    def __init__(self, binary: str | None = None) -> None:
        self.binary = (
            binary
            or os.environ.get("AUTOPALETTE_SCHEMER2")
            or shutil.which("schemer2")
        )

    def extract(self, image: Path, cfg: PaletteConfig) -> Extraction:
        if not self.binary:
            raise RuntimeError(
                "schemer2 backend selected but the 'schemer2' binary was not found "
                "(pass --schemer2-bin, set $AUTOPALETTE_SCHEMER2, or put it on PATH)"
            )

        with tempfile.NamedTemporaryFile("r", suffix=".txt", delete=False) as tmp:
            out_path = tmp.name
        try:
            subprocess.run(
                [
                    self.binary,
                    "-format", "img::colors",
                    "-in", str(image),
                    "-out", out_path,
                    "-threshold", str(int(cfg.merge_delta_e * 1000)),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            with open(out_path, "r", encoding="utf-8") as fh:
                hexes = [line.strip() for line in fh if line.strip()]
        finally:
            try:
                os.unlink(out_path)
            except OSError:
                pass

        return Extraction.from_hexes(hexes)
