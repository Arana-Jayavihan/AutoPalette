"""Command-line interface for autopalette.

A pure ``wallpaper -> palette`` transform: it takes an image path plus output
options and knows nothing about any particular nix flake, ``options.nix`` or
``$flakeDir``. Flake-specific wiring lives in the Home-Manager module and the
caller's glue script.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from pathlib import Path

from . import extract, render
from .config import PaletteConfig
from .palette import synthesize
from .quality import score_palette
from .roles import BASE16_ROLES

log = logging.getLogger("autopalette")

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


def _config_from_args(args: argparse.Namespace) -> PaletteConfig:
    return PaletteConfig(mode=args.mode).with_metadata(
        name=args.name, slug=args.slug or args.name, author=args.author
    )


def _generate(wallpaper: Path, cfg: PaletteConfig, *, extractor_name: str,
              schemer2_bin: str | None, seed: int | None) -> dict[str, str]:
    extractor = extract.get_extractor(extractor_name, schemer2_bin=schemer2_bin)
    extraction = extractor.extract(wallpaper, cfg)
    return synthesize(extraction, cfg, rng=random.Random(seed))


# --- generate ---------------------------------------------------------------


def _cmd_generate(args: argparse.Namespace) -> int:
    if not args.wallpaper.is_file():
        log.error("wallpaper not found: %s", args.wallpaper)
        return 1

    cfg = _config_from_args(args)
    try:
        palette = _generate(args.wallpaper, cfg, extractor_name=args.extractor,
                            schemer2_bin=args.schemer2_bin, seed=args.seed)
    except Exception as exc:  # noqa: BLE001 - surface backend failures cleanly
        log.error("palette generation failed: %s", exc)
        return 1

    output = render.render(palette, cfg, args.fmt)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
        log.info("wrote %s palette to %s", args.fmt, args.out)
    else:
        sys.stdout.write(output)
    return 0


# --- score ------------------------------------------------------------------


def _load_palette_json(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    palette = data.get("palette", data)
    return {role: palette[role] for role in BASE16_ROLES}


def _print_report(label: str, palette: dict[str, str], cfg: PaletteConfig) -> bool:
    report = score_palette(palette, cfg)
    status = "PASS" if report.passed else "FAIL"
    print(f"{label}: {report.score:5.1f}/100  [{status}]")
    for c in report.checks:
        mark = "✓" if c.passed else "✗"
        print(f"    {mark} {c.name:<16} {c.detail}")
    return report.passed


def _cmd_score(args: argparse.Namespace) -> int:
    cfg = _config_from_args(args)

    if args.palette:
        _print_report(args.palette.name, _load_palette_json(args.palette), cfg)
        return 0

    if args.wallpaper:
        palette = _generate(args.wallpaper, cfg, extractor_name=args.extractor,
                            schemer2_bin=args.schemer2_bin, seed=args.seed)
        ok = _print_report(args.wallpaper.name, palette, cfg)
        return 0 if ok else 1

    if args.corpus:
        images = sorted(p for p in args.corpus.iterdir()
                        if p.suffix.lower() in _IMAGE_SUFFIXES)
        if not images:
            log.error("no images found in %s", args.corpus)
            return 1
        scores: list[float] = []
        passed = 0
        failures: list[tuple[str, float, list[str]]] = []
        for img in images:
            try:
                palette = _generate(img, cfg, extractor_name=args.extractor,
                                    schemer2_bin=args.schemer2_bin, seed=args.seed)
            except Exception as exc:  # noqa: BLE001
                log.warning("%s: %s", img.name, exc)
                continue
            report = score_palette(palette, cfg)
            scores.append(report.score)
            if report.passed:
                passed += 1
            else:
                failures.append((img.name, report.score,
                                 [c.name for c in report.failures()]))
        n = len(scores)
        rate = 100.0 * passed / n if n else 0.0
        print(f"\ncorpus: {args.corpus}")
        print(f"  images scored : {n}")
        print(f"  pass rate     : {passed}/{n} ({rate:.1f}%)")
        print(f"  mean score    : {sum(scores) / n:.1f}" if n else "  mean score: n/a")
        print(f"  min score     : {min(scores):.1f}" if n else "")
        if failures:
            print(f"  failures ({len(failures)}):")
            for name, sc, checks in sorted(failures, key=lambda f: f[1])[:20]:
                print(f"    {sc:5.1f}  {name:<24} {', '.join(checks)}")
        return 0 if rate >= 95.0 else 1

    log.error("score needs one of --wallpaper, --palette or --corpus")
    return 2


# --- parser -----------------------------------------------------------------


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--extractor", choices=extract.AVAILABLE, default="pillow",
                   help="colour extraction backend (default: pillow)")
    p.add_argument("--mode", choices=["dark", "light", "auto"], default="auto",
                   help="theme mode (default: auto, from wallpaper luminance)")
    p.add_argument("--name", default="auto-generated", help="palette name metadata")
    p.add_argument("--slug", default=None, help="palette slug (defaults to --name)")
    p.add_argument("--author", default="Lucifer 🍃", help="palette author metadata")
    p.add_argument("--seed", type=int, default=None, help="RNG seed")
    p.add_argument("--schemer2-bin", dest="schemer2_bin", default=None,
                   help="path to the schemer2 binary (schemer2 backend only)")
    p.add_argument("-v", "--verbose", action="store_true", help="debug logging")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autopalette",
        description="Generate a base16 colour palette from a wallpaper image.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="generate a palette from a wallpaper")
    gen.add_argument("--wallpaper", required=True, type=Path, help="source image")
    gen.add_argument("--format", dest="fmt", choices=render.FORMATS, default="nix",
                     help="output format (default: nix)")
    gen.add_argument("--out", type=Path, default=None, help="output file (default: stdout)")
    _add_common(gen)
    gen.set_defaults(func=_cmd_generate)

    sc = sub.add_parser("score", help="score palette quality (file, wallpaper or corpus)")
    g = sc.add_mutually_exclusive_group(required=True)
    g.add_argument("--wallpaper", type=Path, help="generate from this image and score it")
    g.add_argument("--palette", type=Path, help="score an existing JSON palette")
    g.add_argument("--corpus", type=Path, help="score every image in this directory")
    _add_common(sc)
    sc.set_defaults(func=_cmd_score)

    return parser


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
