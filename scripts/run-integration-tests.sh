#!/bin/bash
set -e
cd "$(dirname "$0")"

# explicitly set a short TMPDIR to prevent path too long issue on macosx
export TMPDIR=/tmp

echo "build test contracts"
cd ../integration_tests/contracts
HUSKY_SKIP_INSTALL=1 npm install
npm run typechain
cd ..

TESTS_TO_RUN="${TESTS_TO_RUN:-all}"

if [[ "$TESTS_TO_RUN" == "all" ]]; then
  echo "run all tests"
  pytest -v -s -m unmarked
else
  echo "run tests matching $TESTS_TO_RUN"
  export RPC="https://rpc.archive.canary.mantrachain.dev"
  export EVM_RPC="https://evm.archive.canary.mantrachain.dev"
  export EVM_RPC_WS="https://evm.archive.canary.mantrachain.dev/ws"
  export CHAIN_ID="mantra-canary-net-1"
  pytest -vv -s -m connect
fi
