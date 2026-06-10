"""Opt-in extractor that shells out to the ``schemer2`` Go binary.

This reproduces the original pipeline's colour extraction. The binary is located
via (in order) an explicit path, ``$AUTOPALETTE_SCHEMER2``, or ``$PATH``. The
package never hard-depends on it; selecting this backend without the binary
present raises a clear error.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


class Schemer2Extractor:
    def __init__(self, binary: str | None = None) -> None:
        self.binary = (
            binary
            or os.environ.get("AUTOPALETTE_SCHEMER2")
            or shutil.which("schemer2")
        )

    def extract(self, image: Path, *, count: int = 16, threshold: int = 70) -> list[str]:
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
                    "-threshold", str(threshold),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            with open(out_path, "r", encoding="utf-8") as fh:
                colors = [line.strip() for line in fh if line.strip()]
        finally:
            try:
                os.unlink(out_path)
            except OSError:
                pass

        return colors[:count] if count else colors
