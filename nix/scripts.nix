{ pkgs
, config
}: rec {
  start-geth = pkgs.writeShellScriptBin "start-geth" ''
    export PATH=${pkgs.test-env}/bin:${pkgs.go-ethereum}/bin:$PATH
    source ${config.dotenv}
    ${../scripts/start-geth.sh} ${config.geth-genesis} $@
  '';
  start-beacon = pkgs.writeShellScriptBin "start-beacon" ''
    export USE_PRYSM_VERSION=v6.0.4
    ../scripts/prysm.sh beacon-chain --download-only
    ${../scripts/start-beacon.sh} $@
  '';
  start-validator = pkgs.writeShellScriptBin "start-validator" ''
    export USE_PRYSM_VERSION=v6.0.4
    ../scripts/prysm.sh validator --download-only
    ${../scripts/start-validator.sh} $@
  '';
  start-scripts = pkgs.symlinkJoin {
    name = "start-scripts";
    paths = [ start-geth start-beacon start-validator ];
  };
}
