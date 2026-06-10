{ lib
, buildGoModule
, fetchgit
, libvirt
, libxml2
}:

# Opt-in colour-extraction backend. Vendored here (moved out of the consuming
# flake) so anyone selecting the `schemer2` extractor can get the binary from
# this flake instead of packaging it themselves.
buildGoModule {
  pname = "schemer2";
  version = "2";

  src = fetchgit {
    url = "https://github.com/Arana-Jayavihan/schemer2";
    hash = "sha256-Zo/bjBTHYAsGtJAi20ywwCYdqTPzBQ6ypK4w3uV00aE=";
  };

  vendorHash = null;
  env.CGO_ENABLED = 1;

  buildInputs = [ libvirt libxml2 ];

  meta = {
    description = "Extract colours and convert images to ANSI/colour formats";
    homepage = "https://github.com/Arana-Jayavihan/schemer2";
    mainProgram = "schemer2";
    platforms = lib.platforms.linux;
  };
}
