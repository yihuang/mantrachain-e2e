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
  version = "v7.0.0-rc2";
  owner = "MANTRA-Chain";
  rev = "0190aa36619b7f07e19acb762c43a57ad90271eb"; 
  hash = "sha256-+z6C4RInPvKjdKMRB/Kg9w81pxZ7e/Qz/k+1g8C3Oo0=";
  vendorHash = "sha256-v7/jQi8tsFIPJesJ9nehe+RsMv9dJunQuwZHiylVNwE=";
}
