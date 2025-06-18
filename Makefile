#!/usr/bin/make -f

test-e2e-nix:
	@nix-shell ./integration_tests/shell.nix --run "TESTS_TO_RUN=all ./scripts/run-integration-tests.sh"

test-canary-e2e-nix:
	@nix-shell ./integration_tests/shell.nix --run "TESTS_TO_RUN=connect ./scripts/run-integration-tests.sh"
