{ lib, stdenv, buildGoModule, fetchFromGitHub, libobjc, IOKit, nixosTests }:

let
  # A list of binaries to put into separate outputs
  bins = [
    "geth"
    "clef"
  ];

in
buildGoModule rec {
  pname = "go-ethereum";
  version = "v1.15.11";

  src = fetchFromGitHub {
    owner = "ethereum";
    repo = pname;
    rev = "36b2371c59cd91a9b1da062b3e382f05a6d8687e";
    sha256 = "sha256-2XGKkimwe9h8RxO3SzUta5Bh2Ooldl2LiHqUpn8FK7I=";
  };

  proxyVendor = true;
  vendorHash = "sha256-R9Qg6estiyjMAwN6tvuN9ZuE7+JqjEy+qYOPAg5lIJY=";

  doCheck = false;

  outputs = [ "out" ] ++ bins;

  # Move binaries to separate outputs and symlink them back to $out
  postInstall = lib.concatStringsSep "\n" (
    builtins.map (bin: "mkdir -p \$${bin}/bin && mv $out/bin/${bin} \$${bin}/bin/ && ln -s \$${bin}/bin/${bin} $out/bin/") bins
  );

  subPackages = [
    "cmd/abidump"
    "cmd/abigen"
    "cmd/clef"
    "cmd/devp2p"
    "cmd/ethkey"
    "cmd/evm"
    "cmd/geth"
    "cmd/rlpdump"
    "cmd/utils"
  ];

  # Following upstream: https://github.com/ethereum/go-ethereum/blob/v1.10.25/build/ci.go#L218
  tags = [ "urfave_cli_no_docs" ];

  # Fix for usb-related segmentation faults on darwin
  propagatedBuildInputs =
    lib.optionals stdenv.isDarwin [ libobjc IOKit ];

  passthru.tests = { inherit (nixosTests) geth; };

  meta = with lib; {
    homepage = "https://geth.ethereum.org/";
    description = "Official golang implementation of the Ethereum protocol";
    license = with licenses; [ lgpl3Plus gpl3Plus ];
    maintainers = with maintainers; [ adisbladis RaghavSood ];
  };
}
