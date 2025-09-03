# Mantrachain E2E Integration Tests

This repository contains end-to-end integration tests for the MANTRA Chain project, focusing on Cosmos/EVM compatibility, transaction flows, and protocol upgrades.

## Structure

- `integration_tests/`: Python tests for various flows and protocol features.
- `scripts/`: Shell scripts for starting nodes, generating genesis files, and managing test environments.
- `nix/`: Nix expressions for reproducible builds and test environments.

## Usage

### Prerequisites

- [Nix](https://nixos.org/download.html) installed

### Running Tests

1. **Build environment and dependencies:**
   ```sh
   nix-shell integration_tests/shell.nix 
   ```

2. **Configuration (config to set up local nodes):**
   ```sh
   jsonnet --ext-str CHAIN_CONFIG=mantrachaind integration_tests/configs/default.jsonnet | jq
   ```
   or config with other binary 
   ```sh
   jsonnet --ext-str CHAIN_CONFIG=evmd integration_tests/configs/default.jsonnet | jq
   ```

3. **Run tests:**
   ensure all git submodules are initialized and updated:
   ```sh
   git submodule update --init --depth 1 --recursive
   ```
   to try all test
   ```sh
   make test-e2e-nix
   ```
   or specific marker
   ```sh
   pytest -vv -s -m asyncio
   pytest -vv -s -m unmarked
   pytest -vv -s -m slow
   ```
   or more specific
   ```sh
   pytest -vv -s test_basic.py::test_multisig
   ```
   or specific binary
   ```sh
   cd evmd; go build -tags pebbledb -o ../build/evmd ./cmd/evmd; cd ..
   cp build/evmd $GOROOT/bin
   pytest -vv -s test_basic.py::test_simple --chain-config evmd
   ```

### Nix Build Targets

- Build mantrachain for a specific platform:
  ```sh
  nix build .#legacyPackages.aarch64-darwin.mantrachain
  nix build .#legacyPackages.aarch64-linux.mantrachain
  ```

## Key Test Files

- `test_flow.py`: Tests Cosmos/EVM transfer flows and balance assertions.
- `test_eip1559.py`: Tests EIP-1559 dynamic fee transactions and base fee adjustment.
- `test_eip7702.py`: Tests EIP-7702 account abstraction and related flows.
- `test_subscribe.py`: Tests websocket subscriptions and log/event streaming.
- `test_upgrade.py`: Tests cosmovisor-based binary upgrades and verifies chain functionality before and after upgrade.
- `test_fee_history.py`: Tests eth_feeHistory with various scenarios including concurrent requests, parameter changes, and edge cases like beyond-head blocks and invalid percentiles.
- `test_contract.py`: Tests deploy contract with create2 create3 and multicall.
- `test_ibc.py` Tests IBC cross-chain transactions covering OnRecvPacket packet handling (token pairs with IBC coins, tokenfactory coins, native ERC20 tokens) and callback contract interactions.

## Notes

- Some tests are skipped by default (see `@pytest.mark.skip`) and can be enabled as needed.
- Ensure all paths to config files are correct in scripts and Nix expressions.
- For troubleshooting, check logs in the respective data directories and review script outputs.

---

For more details, see comments in each script and test file.