{
  lib,
  stdenv,
  buildGo125Module,
  fetchFromGitHub,
  fetchurl,
  pkgsStatic,
}:
let
  builder = import ../mantrachain-builder.nix {
    inherit lib stdenv buildGo125Module fetchFromGitHub fetchurl pkgsStatic;
  };
in
builder {
  version = "v7";
  owner = "MANTRA-Chain";
  rev = "4464def2d73eafd619e7aaea0190b8844bd92389";
  hash = "sha256-oGjDOnWRfHY8FFfLNGmEDagBpMeRa0I6npZ1Ywk6XbU=";
  vendorHash = "sha256-yL1NRoLIrLjpjqnR3o2UdneUgwtU0K+CbGDDx91qzLk=";
}
