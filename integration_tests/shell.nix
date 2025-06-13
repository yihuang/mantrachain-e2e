{
  system ? builtins.currentSystem,
  pkgs ? import ../nix { inherit system; },
}:
pkgs.mkShell {
  buildInputs = [
    pkgs.mantrachaind
    pkgs.nodejs
    pkgs.test-env
    pkgs.poetry
  ];
  shellHook = ''
    export TMPDIR=/tmp
  '';
}
