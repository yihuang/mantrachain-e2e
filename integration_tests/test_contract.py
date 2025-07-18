import json
from pathlib import Path

import pytest
from eth_contract.create2 import CREATE2_FACTORY, create2_address, create2_deploy
from eth_contract.create3 import CREATEX_FACTORY, create3_address, create3_deploy
from eth_contract.erc20 import ERC20
from eth_contract.multicall3 import (
    MULTICALL3,
    MULTICALL3_ADDRESS,
    Call3Value,
    multicall,
)
from eth_contract.utils import (
    ZERO_ADDRESS,
    balance_of,
    deploy_presigned_tx,
    get_initcode,
)
from eth_contract.weth import WETH
from eth_typing import ChecksumAddress
from eth_utils import to_checksum_address
from web3 import AsyncWeb3
from web3.types import Wei

from .network import setup_custom_mantra


@pytest.fixture(scope="module")
def mantra_replay(tmp_path_factory):
    path = tmp_path_factory.mktemp("mantra-replay")
    yield from setup_custom_mantra(
        path, 26600, Path(__file__).parent / "configs/allow_replay.jsonnet"
    )


async def ensure_create2_deployed(w3: AsyncWeb3):
    "https://github.com/Arachnid/deterministic-deployment-proxy"
    deployer_address = to_checksum_address("0x3fab184622dc19b6109349b94811493bf2a45362")
    tx = bytes.fromhex(
        Path(__file__).parent.joinpath("txs/create2.tx").read_text().strip()[2:]
    )
    await deploy_presigned_tx(
        w3, tx, deployer_address, CREATE2_FACTORY, fee=Wei(10**16)
    )


async def ensure_multicall3_deployed(w3: AsyncWeb3):
    "https://github.com/mds1/multicall3#new-deployments"
    deployer_address = to_checksum_address("0x05f32b3cc3888453ff71b01135b34ff8e41263f2")
    tx = bytes.fromhex(
        Path(__file__).parent.joinpath("txs/multicall3.tx").read_text().strip()[2:]
    )
    await deploy_presigned_tx(w3, tx, deployer_address, MULTICALL3_ADDRESS)


async def ensure_createx_deployed(w3: AsyncWeb3):
    "https://github.com/pcaversaccio/createx#new-deployments"
    deployer_address = to_checksum_address("0xeD456e05CaAb11d66C4c797dD6c1D6f9A7F352b5")
    tx = bytes.fromhex(
        Path(__file__).parent.joinpath("txs/createx.tx").read_text().strip()[2:]
    )
    await deploy_presigned_tx(
        w3, tx, deployer_address, CREATEX_FACTORY, fee=Wei(3 * 10**17)
    )


async def ensure_deployed_by_create2(
    w3: AsyncWeb3, initcode: bytes, salt: bytes | int = 0
) -> ChecksumAddress:
    user = (await w3.eth.accounts)[0]
    if isinstance(salt, int):
        salt = salt.to_bytes(32, "big")
    addr = create2_address(initcode, salt)
    if await w3.eth.get_code(addr):
        print(f"Contract already deployed at {addr}")
        return addr

    print(f"Deploying contract at {addr} using create2")
    return await create2_deploy(w3, user, initcode, salt=salt, value=Wei(0))


MockERC20_ARTIFACT = json.loads(
    Path(__file__).parent.joinpath("contracts/contracts/MockERC20.json").read_text()
)
WETH_SALT = 999
WETH9_ARTIFACT = json.loads(
    Path(__file__).parent.joinpath("contracts/contracts/WETH9.json").read_text()
)
WETH_ADDRESS = create2_address(get_initcode(WETH9_ARTIFACT), WETH_SALT)
MULTICALL3ROUTER_ARTIFACT = json.loads(
    Path(__file__)
    .parent.joinpath("contracts/contracts/Multicall3Router.json")
    .read_text()
)
MULTICALL3ROUTER = create2_address(
    get_initcode(MULTICALL3ROUTER_ARTIFACT, MULTICALL3_ADDRESS)
)


async def deploy_weth(w3: AsyncWeb3) -> None:
    sender = (await w3.eth.accounts)[0]
    address = await create2_deploy(
        w3, sender, get_initcode(WETH9_ARTIFACT), salt=WETH_SALT
    )
    assert address == WETH_ADDRESS, f"Expected {WETH_ADDRESS}, got {address}"


@pytest.mark.asyncio
async def test_flow(mantra_replay):
    w3 = mantra_replay.async_w3
    await ensure_create2_deployed(w3)
    await ensure_multicall3_deployed(w3)
    await ensure_createx_deployed(w3)
    await deploy_weth(w3)
    assert MULTICALL3ROUTER == await ensure_deployed_by_create2(
        w3, get_initcode(MULTICALL3ROUTER_ARTIFACT, MULTICALL3_ADDRESS)
    )
    initcode = get_initcode(MockERC20_ARTIFACT, "TEST", "TEST", 18)
    owner = (await w3.eth.accounts)[0]

    # test_create2_deploy
    salt = 100
    token = await create2_deploy(w3, owner, initcode, salt=salt)
    assert (
        token
        == create2_address(initcode, salt)
        == "0x854d811d90C6E81B84b29C1d7ed957843cF87bba"
    )
    assert await ERC20.fns.balanceOf(owner).call(w3, to=token) == 0
    await ERC20.fns.mint(owner, 1000).transact(w3, owner, to=token)
    assert await ERC20.fns.balanceOf(owner).call(w3, to=token) == 1000

    # test_create3_deploy
    salt = 200
    token = await create3_deploy(
        w3, owner, initcode, salt=salt, factory=CREATEX_FACTORY, value=Wei(0)
    )
    assert (
        token == create3_address(salt) == "0x60f7B32B5799838a480572Aee2A8F0355f607b38"
    )
    assert await ERC20.fns.balanceOf(owner).call(w3, to=token) == 0
    await ERC20.fns.mint(owner, 1000).transact(w3, owner, to=token)
    assert await ERC20.fns.balanceOf(owner).call(w3, to=token) == 1000

    # test_weth
    weth = WETH(to=WETH_ADDRESS)
    before = await balance_of(w3, ZERO_ADDRESS, owner)
    receipt = await weth.fns.deposit().transact(w3, owner, value=1000)
    fee = receipt["effectiveGasPrice"] * receipt["gasUsed"]
    await balance_of(w3, WETH_ADDRESS, owner) == 1000
    receipt = await weth.fns.withdraw(1000).transact(w3, owner)
    fee += receipt["effectiveGasPrice"] * receipt["gasUsed"]
    await balance_of(w3, WETH_ADDRESS, owner) == 0
    assert await balance_of(w3, ZERO_ADDRESS, owner) == before - fee

    # test_batch_call
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
