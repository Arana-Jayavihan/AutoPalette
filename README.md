# AutoPalette

A custom base16 colour palette generator for NixOS.

Point it at a wallpaper image and it emits a 16-colour
[base16](https://github.com/chriskempson/base16) scheme as a nix attrset, JSON,
or an HTML preview.

It is a pure `wallpaper → palette` transform — it knows nothing about any
particular NixOS flake, `options.nix`, or output location. The flake-specific
wiring lives in the provided Home-Manager module and your own glue script.

## Usage

```sh
# nix attrset on stdout (default)
autopalette generate --wallpaper ~/wall.jpg

# write a nix-colors compatible custom.nix
autopalette generate --wallpaper ~/wall.jpg --format nix --out custom.nix

# JSON or an HTML swatch preview
autopalette generate --wallpaper ~/wall.jpg --format json
autopalette generate --wallpaper ~/wall.jpg --format html --out palette.html
```

Run it without installing:

```sh
nix run github:Arana-Jayavihan/autopalette -- generate --wallpaper ~/wall.jpg
```

### Options

| Flag | Default | Meaning |
| --- | --- | --- |
| `--wallpaper` | (required) | Source image path |
| `--extractor` | `pillow` | Colour backend: `pillow` (self-contained) or `schemer2` |
| `--format` | `nix` | `nix`, `json`, or `html` |
| `--out` | stdout | Output file |
| `--colors` | `16` | Candidate colour pool size |
| `--threshold` | `70` | Near-duplicate merge distance |
| `--name` / `--slug` / `--author` | `auto-generated` / `Lucifer 🍃` | Palette metadata |
| `--seed` | random | RNG seed for reproducible output |
| `--schemer2-bin` | PATH | `schemer2` binary (schemer2 backend only) |

## Extractors

* **pillow** (default) — extracts dominant colours with Pillow (median-cut +
  frequency ranking + near-duplicate merging). No external binaries.
* **schemer2** — shells out to the [`schemer2`](https://github.com/Arana-Jayavihan/schemer2)
  Go binary, reproducing the original pipeline. The binary is resolved from
  `--schemer2-bin`, `$AUTOPALETTE_SCHEMER2`, or `$PATH`. This flake also ships it
  as `packages.<system>.schemer2`.

## Nix flake outputs

| Output | Description |
| --- | --- |
| `packages.<system>.autopalette` | The CLI (also `.default`) |
| `packages.<system>.schemer2` | The optional Go extractor backend |
| `homeManagerModules.default` | `programs.autopalette` module |
| `overlays.default` | Adds `autopalette` and `schemer2` to `pkgs` |
| `devShells.default` | Python + Pillow + pytest + ruff |
| `checks.<system>.autopalette` | Runs the pytest suite |

### Home-Manager

```nix
{
  inputs.autopalette.url = "github:Arana-Jayavihan/autopalette";

  # in your home configuration:
  imports = [ inputs.autopalette.homeManagerModules.default ];

  programs.autopalette = {
    enable = true;
    wallpaper = "/home/me/wall.jpg";
    outputFile = "/home/me/flake/config/home/files/autopalette/custom.nix";
    # extractor = "schemer2";
    # schemer2Package = inputs.autopalette.packages.${system}.schemer2;
  };
}
```

This installs the `autopalette` CLI plus an `autopalette-apply` wrapper that
bakes in the configured options. `autopalette-apply [wallpaper]` regenerates the
palette file; pass a path to override the default wallpaper.

> **Note on the generate-then-rebuild model.** The generated palette is consumed
> at nix *evaluation* time (e.g. imported into a nix-colors `colorScheme`), but
> it is produced at *runtime* from an image. So the flow is: run
> `autopalette-apply` to (re)write the palette file, commit it, then rebuild.
> Generation deliberately does **not** happen during evaluation (no IFD / image
> processing at eval time).

## Development

```sh
nix develop          # python + pillow + pytest + ruff
pytest               # run the test suite
ruff check src tests
```
