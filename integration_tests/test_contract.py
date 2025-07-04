import json
from pathlib import Path

import pytest
from eth_contract.create2 import create2_address, create2_deploy
from eth_contract.create3 import create3_address, create3_deploy
from eth_contract.erc20 import ERC20
from eth_contract.utils import deploy_presigned_tx, get_initcode
from web3.types import Wei

from .utils import (
    CONTRACTS,
    CREATE2_FACTORY,
    CREATEX_FACTORY,
    derive_new_account,
)


@pytest.mark.asyncio
async def test_create3_deploy(mantra):
    w3 = mantra.async_w3
    acct = derive_new_account(4)
    tx = bytes.fromhex(
        Path(__file__).parent.joinpath("txs/createx.tx").read_text().strip()[2:]
    )
    factory = CREATEX_FACTORY
    await deploy_presigned_tx(w3, tx, acct.address, factory)
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


@pytest.mark.asyncio
async def test_create2_deploy(mantra):
    w3 = mantra.async_w3
    acct = derive_new_account(5)
    tx = bytes.fromhex(
        Path(__file__).parent.joinpath("txs/create2.tx").read_text().strip()[2:]
    )
    factory = CREATE2_FACTORY
    await deploy_presigned_tx(w3, tx, acct.address, factory)
    artifact = json.loads(CONTRACTS["MockERC20"].read_text())
    initcode = get_initcode(artifact, "TEST", "TEST", 18)
    salt = 200
    owner = (await w3.eth.accounts)[0]
    token = await create2_deploy(
        w3, owner, initcode, salt=salt, factory=factory, gas=3000000, value=Wei(0)
    )
    assert token == create2_address(initcode, salt, factory=factory)
    assert await ERC20.fns.balanceOf(owner).call(w3, to=token) == 0
    await ERC20.fns.mint(owner, 1000).transact(w3, owner, to=token)
    assert await ERC20.fns.balanceOf(owner).call(w3, to=token) == 1000
