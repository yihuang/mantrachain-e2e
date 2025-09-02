import pytest
import web3
from eth_contract.erc20 import ERC20
from eth_contract.weth import WETH
from eth_utils import to_checksum_address

from .utils import ACCOUNTS, DEFAULT_DENOM

WOM = to_checksum_address("0x4200000000000000000000000000000000000006")


@pytest.mark.asyncio
async def test_static_erc20(mantra):
    w3 = mantra.async_w3
    acct = ACCOUNTS["community"]
    addr = acct.address
    balance = await ERC20.fns.balanceOf(addr).call(w3, to=WOM)
    assert balance > 0

    # deposit should be nop
    before = await w3.eth.get_balance(addr)
    print("intial balance", before)
    receipt = await WETH.fns.deposit().transact(w3, acct, value=10**18, to=WOM)
    fee = receipt["effectiveGasPrice"] * receipt["gasUsed"]
    after = await w3.eth.get_balance(addr)
    assert after == before - fee

    # withdraw should be nop
    before = await w3.eth.get_balance(addr)
    receipt = await WETH.fns.withdraw(100).transact(w3, acct, to=WOM)
    fee = receipt["effectiveGasPrice"] * receipt["gasUsed"]
    after = await w3.eth.get_balance(addr)
    assert after == before - fee

    # fail
    msg = "execution reverted"
    with pytest.raises(web3.exceptions.ContractLogicError, match=msg):
        assert await ERC20.fns.decimals().call(w3, to=WOM) == 9
    with pytest.raises(web3.exceptions.ContractLogicError, match=msg):
        assert await ERC20.fns.symbol().call(w3, to=WOM) == DEFAULT_DENOM
    with pytest.raises(web3.exceptions.ContractLogicError, match=msg):
        assert await ERC20.fns.name().call(w3, to=WOM) == DEFAULT_DENOM
