{
  lib,
  buildGoApplication,
  fetchFromGitHub,
}:
buildGoApplication rec {
  pname = "mantrachain";
  version = "v5.0.0-evm";
  src = fetchFromGitHub {
    owner = "MANTRA-Chain";
    repo = pname;
    rev = "7a7a82da7497ebb3d1f89fad044b802cb679965f";
    hash = "sha256-td2ZpJVx/SZaJDAHyrm8FGKLaAhbA3lUMwj+auupm54=";
  };
  modules = ./gomod2nix.toml;
  subPackages = [ "cmd/mantrachaind" ];
  # pwd = src; # needed to support replace

  doCheck = false;
  meta = with lib; {
    description = "MANTRA is a purpose-built RWA Layer 1 Blockchain, capable of adherence to real world regulatory requirements.";
    homepage = "https://github.com/MANTRA-Chain/mantrachain/";
    license = licenses.asl20;
    mainProgram = "mantrachaind" + stdenv.hostPlatform.extensions.executable;
    platforms = platforms.all;
  };
}
