#!/usr/bin/make -f

test-e2e-nix:
	cp scripts/env.template scripts/.env
	@nix-shell ./integration_tests/shell.nix --run "INCLUDE_MANTRACHAIND=true ./scripts/run-integration-tests.sh"

test-e2e-nix-skip-mantrachaind-build:
	cp scripts/env.template scripts/.env
	@nix-shell ./integration_tests/shell.nix --arg includeMantrachaind false --run "INCLUDE_MANTRACHAIND=false ./scripts/run-integration-tests.sh"

test-connect-e2e-nix:
	@nix-shell ./integration_tests/shell.nix --run "TESTS_TO_RUN=connect ./scripts/run-integration-tests.sh"

lint-py:
	flake8 --show-source --count --statistics \
          --format="::error file=%(path)s,line=%(row)d,col=%(col)d::%(path)s:%(row)d:%(col)d: %(code)s %(text)s" \
