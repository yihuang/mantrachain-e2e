#!/usr/bin/make -f

test-e2e-nix:
	TESTS_TO_RUN=all
	@nix-shell ./integration_tests/shell.nix --run ./scripts/run-integration-tests.sh
