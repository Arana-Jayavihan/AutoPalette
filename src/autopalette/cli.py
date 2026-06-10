"""Command-line interface for autopalette.

A pure ``wallpaper -> palette`` transform: it takes an image path plus output
options and knows nothing about any particular nix flake, ``options.nix`` or
``$flakeDir``. Flake-specific wiring lives in the Home-Manager module and the
caller's glue script.
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
from pathlib import Path

from . import extract, render
from .config import PaletteConfig
from .palette import generate_palette

log = logging.getLogger("autopalette")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autopalette",
        description="Generate a base16 colour palette from a wallpaper image.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="generate a palette from a wallpaper")
    gen.add_argument("--wallpaper", required=True, type=Path, help="path to the source image")
    gen.add_argument(
        "--extractor", choices=extract.AVAILABLE, default="pillow",
        help="colour extraction backend (default: pillow)",
    )
    gen.add_argument(
        "--format", dest="fmt", choices=render.FORMATS, default="nix",
        help="output format (default: nix)",
    )
    gen.add_argument(
        "--out", type=Path, default=None,
        help="write output to this file instead of stdout",
    )
    gen.add_argument("--colors", type=int, default=16, help="size of the candidate colour pool")
    gen.add_argument("--threshold", type=int, default=70, help="near-duplicate merge threshold")
    gen.add_argument("--name", default="auto-generated", help="palette name metadata")
    gen.add_argument("--slug", default=None, help="palette slug metadata (defaults to --name)")
    gen.add_argument("--author", default="Lucifer 🍃", help="palette author metadata")
    gen.add_argument("--seed", type=int, default=None, help="RNG seed for reproducible output")
    gen.add_argument(
        "--schemer2-bin", dest="schemer2_bin", default=None,
        help="path to the schemer2 binary (schemer2 backend only)",
    )
    gen.add_argument("-v", "--verbose", action="store_true", help="enable debug logging")
    gen.set_defaults(func=_cmd_generate)
    return parser


def _cmd_generate(args: argparse.Namespace) -> int:
    if not args.wallpaper.is_file():
        log.error("wallpaper not found: %s", args.wallpaper)
        return 1

    extractor = extract.get_extractor(args.extractor, schemer2_bin=args.schemer2_bin)
    try:
        pool = extractor.extract(args.wallpaper, count=args.colors, threshold=args.threshold)
    except Exception as exc:  # noqa: BLE001 - surface any backend failure cleanly
        log.error("colour extraction failed: %s", exc)
        return 1

    config = PaletteConfig().with_metadata(
        name=args.name, slug=args.slug or args.name, author=args.author
    )
    rng = random.Random(args.seed)

    try:
        palette = generate_palette(pool, config, rng=rng)
    except ValueError as exc:
        log.error("%s", exc)
        return 1

    output = render.render(palette, config, args.fmt)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
        log.info("wrote %s palette to %s", args.fmt, args.out)
    else:
        sys.stdout.write(output)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
        format="autopalette: %(message)s",
    )
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
