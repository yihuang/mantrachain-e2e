#!/bin/sh
set -e

DATA=$1
if [ -z $DATA ]; then
    echo "No data directory supplied"
    exit 1
fi
shift

VALIDATOR_BIN=$(ls ../scripts/dist/validator-v6.0.4-* 2>/dev/null | head -n 1)
if [ ! -f "$VALIDATOR_BIN" ]; then
    echo "validator binary not found!"
    exit 1
fi

$VALIDATOR_BIN \
--datadir $DATA \
--accept-terms-of-use \
--interop-num-validators=1 \
--chain-config-file=config.yaml