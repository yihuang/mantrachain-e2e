import pytest
from eth_contract.deploy_utils import (
    ensure_create2_deployed,
    ensure_deployed_by_create2,
)
from eth_contract.erc20 import ERC20
from eth_contract.utils import ZERO_ADDRESS, balance_of, get_initcode
from eth_contract.weth import WETH

from .utils import (
    ACCOUNTS,
    WETH9_ARTIFACT,
    WETH_ADDRESS,
    WETH_SALT,
    module_address,
    submit_gov_proposal,
)


@pytest.mark.asyncio
async def test_static_erc20(mantra, tmp_path):
    w3 = mantra.async_w3
    account = ACCOUNTS["community"]
    await ensure_create2_deployed(w3, account)
    await ensure_deployed_by_create2(
        w3,
        account,
        get_initcode(WETH9_ARTIFACT),
        salt=WETH_SALT,
    )

    owner = account.address
    submit_gov_proposal(
        mantra,
        tmp_path,
        messages=[
            {
                "@type": "/cosmos.evm.erc20.v1.MsgRegisterERC20",
                "signer": module_address("gov"),
                "erc20addresses": [WETH_ADDRESS],
            },
        ],
        gas=300000,
    )
    cli = mantra.cosmos_cli()
    cli.query_erc20_token_pairs()
    # deposit should be nop
    before = await w3.eth.get_balance(owner)
    weth = WETH(to=WETH_ADDRESS)
    before = await balance_of(w3, ZERO_ADDRESS, owner)
    receipt = await weth.fns.deposit().transact(w3, account, value=1000)
    fee = receipt["effectiveGasPrice"] * receipt["gasUsed"]
    await balance_of(w3, WETH_ADDRESS, owner) == 1000
    receipt = await weth.fns.withdraw(1000).transact(w3, account)
    fee += receipt["effectiveGasPrice"] * receipt["gasUsed"]
    await balance_of(w3, WETH_ADDRESS, owner) == 0

    # withdraw should be nop
    weth = WETH(to=WETH_ADDRESS)
    before = await balance_of(w3, ZERO_ADDRESS, owner)
    receipt = await weth.fns.deposit().transact(w3, account, value=1000)
    fee = receipt["effectiveGasPrice"] * receipt["gasUsed"]
    await balance_of(w3, WETH_ADDRESS, owner) == 1000
    receipt = await weth.fns.withdraw(1000).transact(w3, account)
    fee += receipt["effectiveGasPrice"] * receipt["gasUsed"]
    await balance_of(w3, WETH_ADDRESS, owner) == 0
    assert await balance_of(w3, ZERO_ADDRESS, owner) == before - fee

    # fail
    assert await ERC20.fns.decimals().call(w3, to=WETH_ADDRESS) == 18
    assert await ERC20.fns.symbol().call(w3, to=WETH_ADDRESS) == "WETH"
    assert await ERC20.fns.name().call(w3, to=WETH_ADDRESS) == "Wrapped Ether"
