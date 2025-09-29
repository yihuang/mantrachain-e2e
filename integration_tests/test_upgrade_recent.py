import time

import pytest
from eth_contract.erc20 import ERC20

from .network import Mantra
from .upgrade_utils import (
    cleanup_upgrades_folder,
    do_upgrade,
    setup_mantra_upgrade,
)
from .utils import (
    ADDRS,
    assert_create_tokenfactory_denom,
    assert_mint_tokenfactory_denom,
    assert_tf_flow,
    bech32_to_eth,
    denom_to_erc20_address,
    derive_new_account,
    wait_for_new_blocks,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module")
def custom_mantra(request, tmp_path_factory):
    chain = request.config.getoption("chain_config")
    yield from setup_mantra_upgrade(
        tmp_path_factory,
        "upgrade-test-package",
        "cosmovisor_recent",
        "v5.0.0-rc3",
        chain=chain,
    )


async def exec(c):
    cli = c.cosmos_cli()
    community = "community"
    gas = 300000

    nodes = [f"mantra-canary-net-1-node{i}" for i in range(3)]
    c.supervisorctl("start", *nodes)
    wait_for_new_blocks(cli, 1)

    height = cli.block_height()
    target_height = height + 15
    addr_a = cli.address(community)
    signer1 = bech32_to_eth(addr_a)
    subdenom = f"admin{time.time()}"
    denom = assert_create_tokenfactory_denom(
        cli, subdenom, is_legacy=True, _from=addr_a, gas=620000
    )
    tf_erc20_addr = denom_to_erc20_address(denom)
    tf_amt = 10**6
    w3 = c.async_w3
    balance_eth = await ERC20.fns.balanceOf(signer1).call(w3, to=tf_erc20_addr)
    balance = cli.balance(addr_a, denom)
    balance = assert_mint_tokenfactory_denom(cli, denom, tf_amt, _from=addr_a, gas=gas)
    balance_eth = await ERC20.fns.balanceOf(signer1).call(w3, to=tf_erc20_addr)
    total = await ERC20.fns.totalSupply().call(w3, to=tf_erc20_addr)
    assert total == balance == balance_eth == tf_amt

    cli = do_upgrade(c, "v5.0.0-rc4", target_height)
    balance_eth = await ERC20.fns.balanceOf(signer1).call(w3, to=tf_erc20_addr)
    total = await ERC20.fns.totalSupply().call(w3, to=tf_erc20_addr)
    balance = cli.balance(addr_a, denom)
    # miss migrate for dynamic precompiles
    assert total == balance_eth == 0
    assert balance == tf_amt

    height = cli.block_height()
    target_height = height + 15

    cli = do_upgrade(c, "v5.0.0-rc5", target_height)
    balance_eth = await ERC20.fns.balanceOf(signer1).call(w3, to=tf_erc20_addr)
    total = await ERC20.fns.totalSupply().call(w3, to=tf_erc20_addr)
    balance = cli.balance(addr_a, denom)
    assert total == balance == balance_eth == tf_amt

    receiver = derive_new_account(5).address
    await assert_tf_flow(w3, receiver, signer1, ADDRS["signer2"], tf_erc20_addr)
    c.supervisorctl("stop", "all")
    state = cli.export()["app_state"]
    assert state["erc20"]["native_precompiles"] == [
        "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
    ]

    c.supervisorctl("start", *nodes)
    wait_for_new_blocks(cli, 1)

    height = cli.block_height()
    target_height = height + 15

    cli = do_upgrade(c, "v5.0.0-rc6", target_height)

    height = cli.block_height()
    target_height = height + 15

    cli = do_upgrade(c, "v5.0.0-rc7", target_height)

    height = cli.block_height()
    target_height = height + 15

    cli = do_upgrade(c, "v5.0.0-rc8", target_height)

    height = cli.block_height()
    target_height = height + 15

    cli = do_upgrade(c, "v5.0.0-rc9", target_height)


async def test_cosmovisor_upgrade(custom_mantra: Mantra):
    await exec(custom_mantra)
    cleanup_upgrades_folder(custom_mantra.cosmos_cli().data_dir)
