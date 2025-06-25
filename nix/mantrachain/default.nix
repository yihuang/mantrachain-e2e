{
  lib,
  stdenv,
  buildGo123Module,
  fetchFromGitHub,
  nix-gitignore,
  darwin,
  rev ? "dirty",
  static ? stdenv.hostPlatform.isStatic,
  nativeByteOrder ? true, # nativeByteOrder mode will panic on big endian machines
  fetchurl,
  pkgsStatic,
}:
let
  version = "v5.0.0-rc2";
  pname = "mantrachain";
  wasmvmVersion = "v2.2.4";

  # Use static packages for Linux to ensure musl compatibility
  buildPackages = if stdenv.isLinux then pkgsStatic else { inherit stdenv buildGo123Module; };
  buildStdenv = buildPackages.stdenv;
  buildGo123Module' = if stdenv.isLinux then buildPackages.buildGo123Module else buildGo123Module;

  # Download wasmvm libraries as fixed-output derivations
  wasmvmLibs = {
    darwin = fetchurl {
      url = "https://github.com/CosmWasm/wasmvm/releases/download/${wasmvmVersion}/libwasmvmstatic_darwin.a";
      sha256 = "sha256-Q/E0EBUUPGJrY0pwmHLv6EjkWtJERMCRSW+cZI/XGmc=";
    };
    linux-x86_64 = fetchurl {
      url = "https://github.com/CosmWasm/wasmvm/releases/download/${wasmvmVersion}/libwasmvm_muslc.x86_64.a";
      sha256 = "sha256-cMmJaE0rSMoXu9VbtpS7sTbXXDk8Bn7zvbyjHSsjtXg=";
    };
    linux-aarch64 = fetchurl {
      url = "https://github.com/CosmWasm/wasmvm/releases/download/${wasmvmVersion}/libwasmvm_muslc.aarch64.a";
      sha256 = "sha256-J/sTgh28UZEZ9PmMMKQssyQpsRGw/ciDaGw0pBd3SI8=";
    };
  };

  wasmvmLib = 
    if buildStdenv.isDarwin then wasmvmLibs.darwin
    else if buildStdenv.isLinux && buildStdenv.hostPlatform.isAarch64 then wasmvmLibs.linux-aarch64
    else if buildStdenv.isLinux then wasmvmLibs.linux-x86_64
    else throw "Unsupported platform for wasmvm";

  tags = [
    "ledger"
    "netgo"
    "osusergo"
    "pebbledb"
  ] ++ lib.optionals nativeByteOrder [ "nativebyteorder" ]
    ++ lib.optionals buildStdenv.isDarwin [ "static_wasm" ]
    ++ lib.optionals buildStdenv.isLinux [ "muslc" ];

  ldflags = [
    "-X github.com/cosmos/cosmos-sdk/version.Name=mantrachain"
    "-X github.com/cosmos/cosmos-sdk/version.AppName=${pname}"
    "-X github.com/cosmos/cosmos-sdk/version.Version=${version}"
    "-X github.com/cosmos/cosmos-sdk/version.BuildTags=${lib.concatStringsSep "," tags}"
    "-X github.com/cosmos/cosmos-sdk/version.Commit=${rev}"
  ] ++ [
    "-w"
    "-s"
    "-linkmode=external"
  ] ++ lib.optionals buildStdenv.isLinux [
    "-extldflags '-static -lm'"
  ];

in
buildGo123Module' rec {
  inherit
    pname
    version
    tags
    ldflags
    ;
  stdenv = buildStdenv;
  src = fetchFromGitHub {
    owner = "mmsqe";
    repo = pname;
    rev = "dfecaa8f9fe76bdbec23da2cbafd85ca8a061dce";
    hash = "sha256-RqqN2kUhiBfyExarjkocN3u9wVspLZIRpRYqZIYuGKU=";
  };
  vendorHash = "sha256-lSNN3h7OkahXYLyoETi3Zg+sio0ABq+2OFQ0/R1KvlI=";
  proxyVendor = true;
  subPackages = [ "cmd/mantrachaind" ];
  CGO_ENABLED = "1";

  preBuild = ''
    mkdir -p $TMPDIR/lib
    cp ${wasmvmLib} $TMPDIR/lib/$(basename ${wasmvmLib.name})
    export CGO_LDFLAGS="-L$TMPDIR/lib $CGO_LDFLAGS"
  '';

  doCheck = false;
  meta = with lib; {
    description = "Official implementation of the mantra protocol";
    homepage = "https://www.mantrachain.io/";
    license = licenses.asl20;
    mainProgram = "mantrachaind" + buildStdenv.hostPlatform.extensions.executable;
    platforms = platforms.all;
  };
}