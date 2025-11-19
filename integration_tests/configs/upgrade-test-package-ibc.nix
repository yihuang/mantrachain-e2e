{ 
  pkgs ? (builtins.getFlake (toString ../..)).legacyPackages.${builtins.currentSystem or "x86_64-linux"}, includeMantrachaind ? true
}:
let
  common = import ./mantrachain-common.nix { inherit pkgs; };
  platform = common.platform;
  releases = {
    genesis = pkgs.callPackage ../../nix/v6.1.1/default.nix {};
  } // (
    pkgs.lib.optionalAttrs includeMantrachaind {
      "v7.0.0-rc2" = pkgs.mantrachaind;
    }
  ) // (
    pkgs.lib.optionalAttrs (!includeMantrachaind) {
      "v7.0.0-rc2" = pkgs.writeShellScriptBin "mantrachaind" ''
        exec mantrachaind "$@"
      '';
    }
  );
in
pkgs.linkFarm "upgrade-test-package" (
  pkgs.lib.mapAttrsToList (name: path: { inherit name path; }) releases
)
