import json
from pathlib import Path

import pytest
from eth_contract.create3 import create3_address, create3_deploy
from eth_contract.erc20 import ERC20
from eth_contract.utils import deploy_presigned_tx, get_initcode
from web3.types import Wei

from .utils import CONTRACTS, CREATEX_FACTORY, derive_new_account, send_transaction


@pytest.mark.asyncio
async def test_create3_deploy(mantra):
    w3 = mantra.async_w3
    acct = derive_new_account(4)
    fee = Wei(10**18)  # 1 ETH
    tx = {
        "to": acct.address,
        "value": fee,
    }
    res = send_transaction(mantra.w3, tx)
    assert res.status == 1
    tx = bytes.fromhex(
        Path(__file__).parent.joinpath("txs/createx.tx").read_text().strip()[2:]
    )
    factory = CREATEX_FACTORY
    deployer = acct.address
    await deploy_presigned_tx(w3, tx, deployer, factory)
    artifact = json.loads(CONTRACTS["MockERC20"].read_text())
    initcode = get_initcode(artifact, "TEST", "TEST", 18)
    salt = 200
    owner = (await w3.eth.accounts)[0]
    token = await create3_deploy(
        w3, owner, initcode, salt=salt, factory=factory, value=Wei(0)
    )
    assert token == create3_address(salt, factory=factory)
    assert await ERC20.fns.balanceOf(owner).call(w3, to=token) == 0
    await ERC20.fns.mint(owner, 1000).transact(w3, owner, to=token)
    assert await ERC20.fns.balanceOf(owner).call(w3, to=token) == 1000
