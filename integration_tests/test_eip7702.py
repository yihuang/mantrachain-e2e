import pytest
import web3

from .network import Geth
from .utils import ACCOUNTS, ADDRS, KEYS
from .utils import send_transaction as send_transaction_sync


@pytest.fixture(scope="module", params=["mantra", "geth"])
def cluster(request, mantra, geth):
    provider = request.param
    if provider == "mantra":
        yield mantra
    elif provider == "geth":
        yield geth
    else:
        raise NotImplementedError


@pytest.mark.asyncio
async def test_eoa(cluster):
    w3 = cluster.async_w3
    name = "validator"
    acct = ACCOUNTS[name]
    sender = ADDRS[name]
    key = KEYS[name]
    chain_id = await w3.eth.chain_id
    nonce = await w3.eth.get_transaction_count(acct.address)
    authz = acct.sign_authorization(
        {
            "address": "0xdeadbeef00000000000000000000000000000000",
            "chainId": chain_id,
            "nonce": nonce + 1,
        }
    )
    tx = {
        "chainId": chain_id,
        "nonce": nonce,
        "gas": 200_000,
        "maxFeePerGas": 10**11,
        "maxPriorityFeePerGas": 10**11,
        "to": acct.address,
        "value": 0,
        "accessList": [],
        "authorizationList": [authz],
        "data": "0x",
    }
    signed = acct.sign_transaction(tx)
    tx_hash = await w3.eth.send_raw_transaction(signed.raw_transaction)
    res = await w3.eth.wait_for_transaction_receipt(tx_hash)
    assert res.status == 1
    code = await w3.eth.get_code(acct.address)
    assert code.hex().startswith("ef0100deadbeef"), "Code was not set!"

    gas_price = cluster.w3.eth.gas_price
    gas = 21000
    data = {"to": sender, "value": 10000, "gasPrice": gas_price, "gas": gas}
    data["nonce"] = cluster.w3.eth.get_transaction_count(sender) + 1

    if isinstance(cluster, Geth):
        send_transaction_sync(cluster.w3, data, key=key, check=False)
    else:
        with pytest.raises(web3.exceptions.Web3RPCError, match="invalid sequence"):
            send_transaction_sync(cluster.w3, data, key=key, check=False)

    # clear code
    clear_tx = dict(tx)
    clear_tx["nonce"] = nonce + 2
    clear_tx["authorizationList"] = [
        acct.sign_authorization(
            {
                "chainId": chain_id,
                "address": f"0x{'00' * 20}",
                "nonce": nonce + 3,
            }
        )
    ]
    signed_reset = acct.sign_transaction(clear_tx)
    clear_tx_hash = await w3.eth.send_raw_transaction(signed_reset.raw_transaction)
    res = await w3.eth.wait_for_transaction_receipt(clear_tx_hash)
    assert res.status == 1
    reset_code = await w3.eth.get_code(acct.address)
    assert reset_code.hex().startswith(""), "Code was not clear!"

    # TODO: https://github.com/cosmos/evm/issues/493
    # data = {"to": sender, "value": 10000, "gasPrice": gas_price, "gas": gas}
    # send_transaction_sync(cluster.w3, data, key=key)["transactionHash"]
