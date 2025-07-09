import time
from pathlib import Path

import pytest

from .network import setup_custom_mantra
from .utils import wait_for_new_blocks


@pytest.fixture(scope="module")
def custom_mantra(tmp_path_factory):
    path = tmp_path_factory.mktemp("fee-history")
    yield from setup_custom_mantra(
        path, 26700, Path(__file__).parent / "configs/patch.jsonnet"
    )

@pytest.mark.skip(reason="skipping integer overflow test")
def test_int_overflow(custom_mantra):
    cli = custom_mantra.cosmos_cli()
    name = "validator"
    bech32_addr = cli.address(name)
    val_addr = cli.address(name, "val")
    rsp = cli.set_withdraw_addr(bech32_addr, from_=name)
    assert rsp["code"] == 0, rsp["raw_log"]

    # fund validator rewards pool
    denom = "utesttest"
    delegation_amt_w_denom = f"115792089237316195423570985008687907853269984665640564039457584007913129639935{denom}"
    rsp = cli.fund_validator_rewards_pool(
        val_addr,
        delegation_amt_w_denom,
        from_=name,
    )
    assert rsp["code"] == 0, rsp["raw_log"]

    balance = cli.balance(bech32_addr, denom=denom)
    # withdraw rewards
    cli.withdraw_rewards(val_addr, from_=name)
    balance = cli.balance(bech32_addr, denom=denom)

    # stake to this validator
    cli.delegate_amount(
        val_addr,
        f"{10000}stake",
        bech32_addr,
    )

    # fund validator rewards pool again
    rsp = cli.fund_validator_rewards_pool(
        val_addr,
        f"{balance}{denom}",
        from_=name,
    )
    assert rsp["code"] == 0, rsp["raw_log"]
    balance = cli.balance(bech32_addr, denom=denom)

    # stop the validator to trigger slashing due to validator down
    custom_mantra.supervisorctl("stop", "mantra-canary-net-1-node0")
    time.sleep(5)
    custom_mantra.supervisorctl("start", "mantra-canary-net-1-node0")
    wait_for_new_blocks(cli, 2, timeout=30)
