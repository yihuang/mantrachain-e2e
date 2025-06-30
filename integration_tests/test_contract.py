import json

import pytest
from eth_contract.create3 import create3_address, create3_deploy
from eth_contract.erc20 import ERC20
from eth_contract.utils import get_initcode
from web3.types import Wei

from .utils import ADDRS, CONTRACTS, CREATEX_FACTORY


@pytest.mark.asyncio
async def test_create3_deploy(mantra):
    w3 = mantra.async_w3
    owner = ADDRS["community"]
    artifact = json.loads(CONTRACTS["MockERC20"].read_text())
    initcode = get_initcode(artifact, "TEST", "TEST", 18)
    salt = 200
    token = await create3_deploy(
        w3, owner, initcode, salt=salt, factory=CREATEX_FACTORY, value=Wei(0)
    )
    assert token == create3_address(salt, factory=CREATEX_FACTORY)
    assert await ERC20.fns.balanceOf(owner).call(w3, to=token) == 0
    await ERC20.fns.mint(owner, 1000).transact(w3, owner, to=token)
    assert await ERC20.fns.balanceOf(owner).call(w3, to=token) == 1000
