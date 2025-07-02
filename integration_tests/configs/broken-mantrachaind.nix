{ pkgs ? import ../../nix { } }:
let mantrachaind = (pkgs.callPackage ../../nix/mantrachain/. { });
in
mantrachaind.overrideAttrs (oldAttrs: {
  patches = oldAttrs.patches or [ ] ++ [
    ./broken-mantrachaind.patch
  ];
})
