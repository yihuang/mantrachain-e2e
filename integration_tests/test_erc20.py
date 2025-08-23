import pytest
from eth_contract.deploy_utils import (
    ensure_create2_deployed,
    ensure_deployed_by_create2,
)
from eth_contract.utils import get_initcode

from .utils import (
    ACCOUNTS,
    WETH9_ARTIFACT,
    WETH_ADDRESS,
    WETH_SALT,
    assert_register_erc20_denom,
    assert_weth_flow,
)


@pytest.mark.asyncio
async def test_static_erc20(mantra, tmp_path):
    w3 = mantra.async_w3
    account = ACCOUNTS["community"]
    await ensure_create2_deployed(w3, account)
    weth_addr = await ensure_deployed_by_create2(
        w3,
        account,
        get_initcode(WETH9_ARTIFACT),
        salt=WETH_SALT - 100,
    )
    assert weth_addr != WETH_ADDRESS, "should be different weth address"
    assert_register_erc20_denom(mantra, weth_addr, tmp_path)
    await assert_weth_flow(w3, weth_addr, account.address, account)
