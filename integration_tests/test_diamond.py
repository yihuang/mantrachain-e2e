from web3 import AsyncWeb3

from .utils import build_contract


async def test_diamond(mantra):
    w3: AsyncWeb3 = mantra.async_w3
    build_contract("Diamond")
