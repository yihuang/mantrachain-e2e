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
  version = "v8";
  owner = "MANTRA-Chain";
  rev = "6038e2351e266c2b1378dba707a50803fb466811";
  hash = "sha256-BTHpl5SAmE59wMxhiF0EwBpQW7K+/B89gBe1l/S48j8=";
  vendorHash = "sha256-e+tO6ELxvMbbIxDZdweHb6uOKyJbWsX8z/HnIdbI4CI=";
}
