{ lib
, python3Packages
}:

python3Packages.buildPythonApplication {
  pname = "autopalette";
  version = "0.1.0";
  pyproject = true;

  src = lib.cleanSource ../.;

  build-system = [ python3Packages.setuptools ];

  dependencies = [ python3Packages.pillow ];

  nativeCheckInputs = [ python3Packages.pytestCheckHook ];

  pythonImportsCheck = [ "autopalette" ];

  meta = {
    description = "Generate a base16 colour palette from a wallpaper image";
    homepage = "https://github.com/Arana-Jayavihan/autopalette";
    license = lib.licenses.mit;
    mainProgram = "autopalette";
    platforms = lib.platforms.all;
  };
}
