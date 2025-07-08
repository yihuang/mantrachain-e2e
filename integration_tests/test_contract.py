import json
from pathlib import Path
from typing import Any

import pytest
from eth_contract.contract import Contract, ContractFunction
from eth_contract.create2 import create2_address, create2_deploy
from eth_contract.create3 import create3_address, create3_deploy
from eth_contract.erc20 import ERC20
from eth_contract.multicall3 import MULTICALL3_ABI, Call3, Call3Value
from eth_contract.utils import deploy_presigned_tx, get_initcode
from eth_contract.weth import WETH
from eth_typing import ChecksumAddress
from web3 import AsyncWeb3
from web3.types import Wei

from .utils import (
    CONTRACTS,
    derive_new_account,
)

CREATEX_FACTORY = "0x9699e95B84695B451f2aEf9Df12f73B86Bcf3e45"  # derive_new_account(4)
CREATE2_FACTORY = "0x63f9E75Ae275e03651bc53c9F01409603f861ac5"  # derive_new_account(5)
WETH_ADDRESS = "0x151Bf903c88F4fd25663f784C42F1d6786653Bf5"  # derive_new_account(6)
MULTICALL3_ADDRESS = (
    "0x38B2601EB7317AF793DCc5563d3612580a2B40E6"  # derive_new_account(7)
)
MULTICALL3 = Contract(MULTICALL3_ABI, {"to": MULTICALL3_ADDRESS})


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


async def multicall(
    w3: AsyncWeb3,
    calls: list[tuple[ChecksumAddress, ContractFunction]],
    allow_failure=False,
) -> list[Any]:
    call3 = [Call3(target, allow_failure, fn.data) for target, fn in calls]
    results = await MULTICALL3.fns.aggregate3(call3).call(w3)
    values = []
    for (_, fn), (success, data) in zip(calls, results):
        if success and data:
            values.append(fn.decode(data))
        else:
            values.append(None)
    return values


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

    acct = derive_new_account(6)
    salt = 999
    artifact = json.loads(CONTRACTS["WETH9"].read_text())
    initcode = get_initcode(artifact)
    assert create2_address(initcode, salt, factory=factory) == WETH_ADDRESS
    token = await create2_deploy(
        w3,
        owner,
        initcode,
        salt=salt,
        factory=factory,
    )
    assert token == WETH_ADDRESS, token

    acct = derive_new_account(7)
    tx = bytes.fromhex(
        Path(__file__).parent.joinpath("txs/multicall3.tx").read_text().strip()[2:]
    )
    await deploy_presigned_tx(w3, tx, acct.address, MULTICALL3_ADDRESS)

    weth = WETH(to=WETH_ADDRESS)
    users = (await w3.eth.accounts)[:10]
    amount = 1000
    amount_all = amount * len(users)

    balances = [(WETH_ADDRESS, ERC20.fns.balanceOf(user)) for user in users]
    assert all(x == 0 for x in await multicall(w3, balances))
    await MULTICALL3.fns.aggregate3Value(
        [Call3Value(WETH_ADDRESS, False, amount_all, weth.fns.deposit().data)]
        + [
            Call3Value(WETH_ADDRESS, False, 0, ERC20.fns.transfer(user, amount).data)
            for user in users
        ]
    ).transact(w3, users[0], value=amount_all)
    assert all(x == amount for x in await multicall(w3, balances))
