{ config, lib, pkgs, ... }:

let
  cfg = config.programs.autopalette;

  # Self-contained defaults: build from this flake's sources via callPackage so
  # the module works without the consumer applying the overlay.
  defaultPackage = pkgs.callPackage ./package.nix { };

  schemer2Bin = lib.optionalString
    (cfg.extractor == "schemer2" && cfg.schemer2Package != null)
    "--schemer2-bin ${cfg.schemer2Package}/bin/schemer2";

  # A thin wrapper that bakes in the configured options. `autopalette-apply`
  # regenerates the palette file; an optional positional arg overrides the
  # wallpaper (e.g. the live wallpaper picked by a theme switcher).
  applyScript = pkgs.writeShellScriptBin "autopalette-apply" ''
    set -euo pipefail
    exec ${cfg.package}/bin/autopalette generate \
      --wallpaper "''${1:-${cfg.wallpaper}}" \
      --extractor ${cfg.extractor} \
      ${schemer2Bin} \
      --threshold ${toString cfg.threshold} \
      --name ${lib.escapeShellArg cfg.name} \
      --author ${lib.escapeShellArg cfg.author} \
      --format ${cfg.format} \
      --out ${lib.escapeShellArg cfg.outputFile}
  '';
in
{
  options.programs.autopalette = {
    enable = lib.mkEnableOption "autopalette wallpaper palette generator";

    package = lib.mkOption {
      type = lib.types.package;
      default = defaultPackage;
      defaultText = lib.literalExpression "pkgs.callPackage ./package.nix { }";
      description = "The autopalette package to use.";
    };

    wallpaper = lib.mkOption {
      type = lib.types.str;
      description = "Default wallpaper path used by autopalette-apply.";
    };

    extractor = lib.mkOption {
      type = lib.types.enum [ "pillow" "schemer2" ];
      default = "pillow";
      description = "Colour extraction backend.";
    };

    schemer2Package = lib.mkOption {
      type = lib.types.nullOr lib.types.package;
      default = null;
      defaultText = lib.literalExpression "null";
      description = ''
        Package providing the `schemer2` binary, used only when
        `extractor = "schemer2"`. When null, the binary is resolved from PATH.
      '';
    };

    threshold = lib.mkOption {
      type = lib.types.int;
      default = 70;
      description = "Near-duplicate colour merge threshold.";
    };

    name = lib.mkOption {
      type = lib.types.str;
      default = "auto-generated";
      description = "Palette name metadata.";
    };

    author = lib.mkOption {
      type = lib.types.str;
      default = "Lucifer 🍃";
      description = "Palette author metadata.";
    };

    format = lib.mkOption {
      type = lib.types.enum [ "nix" "json" "html" ];
      default = "nix";
      description = "Output format written by autopalette-apply.";
    };

    outputFile = lib.mkOption {
      type = lib.types.str;
      description = "Where autopalette-apply writes the generated palette.";
      example = "/home/user/flake/config/home/files/autopalette/custom.nix";
    };
  };

  config = lib.mkIf cfg.enable {
    home.packages =
      [ cfg.package applyScript ]
      ++ lib.optional (cfg.extractor == "schemer2" && cfg.schemer2Package != null)
        cfg.schemer2Package;
  };
}
