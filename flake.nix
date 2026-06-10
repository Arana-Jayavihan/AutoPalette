{
  description = "Generate a base16 colour palette from a wallpaper image.";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem
      (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          packages = rec {
            autopalette = pkgs.callPackage ./nix/package.nix { };
            schemer2 = pkgs.callPackage ./nix/schemer2.nix { };
            default = autopalette;
          };

          apps.default = {
            type = "app";
            program = "${self.packages.${system}.autopalette}/bin/autopalette";
          };

          checks.autopalette = self.packages.${system}.autopalette;

          devShells.default = pkgs.mkShell {
            packages = [
              (pkgs.python3.withPackages (ps: [ ps.pillow ps.pytest ]))
              pkgs.ruff
            ];
          };

          formatter = pkgs.nixpkgs-fmt;
        })
    // {
      homeManagerModules.default = import ./nix/hm-module.nix;
      homeManagerModules.autopalette = import ./nix/hm-module.nix;

      overlays.default = final: _prev: {
        autopalette = final.callPackage ./nix/package.nix { };
        schemer2 = final.callPackage ./nix/schemer2.nix { };
      };
    };
}
