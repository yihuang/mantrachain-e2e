{
  lib,
  stdenv,
  buildGo123Module,
  fetchFromGitHub,
  fetchurl,
  pkgsStatic,
}:
let
  builder = import ../mantrachain-builder.nix {
    inherit lib stdenv buildGo123Module fetchFromGitHub fetchurl pkgsStatic;
  };
in
builder {
  version = "v7.0.0-rc1";
  owner = "MANTRA-Chain";
  rev = "189cbbcba5561d84772816713c9233a0b51a8471"; 
  hash = "sha256-XNiW/xFfJ6XR0EUG4hakWdHjtbYBTjfANFAtOo+nimE=";
  vendorHash = "sha256-v7/jQi8tsFIPJesJ9nehe+RsMv9dJunQuwZHiylVNwE=";
}
