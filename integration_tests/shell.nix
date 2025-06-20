{
  system ? builtins.currentSystem,
  pkgs ? import ../nix { inherit system; },
  includeMantrachaind ? true,
}:
pkgs.mkShell {
  buildInputs = [
    pkgs.nodejs
    pkgs.test-env
    pkgs.poetry
    pkgs.go-ethereum
    pkgs.start-scripts
  ] ++ pkgs.lib.optionals includeMantrachaind [
    pkgs.mantrachaind
  ];
  shellHook = ''
    export TMPDIR=/tmp
  '';
}
