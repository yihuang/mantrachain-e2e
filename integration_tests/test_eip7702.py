import pytest

from .utils import send_transaction


@pytest.mark.skip(reason="skipping eoa test")
def test_eoa(mantra):
    w3 = mantra.w3
    # fund new acct
    acct = w3.eth.account.create()
    value = 10**22
    tx = {
        "to": acct.address,
        "value": value,
    }
    tx_hash = send_transaction(w3, tx)

    # send 7702 tx
    chain_id = w3.eth.chain_id
    nonce = w3.eth.get_transaction_count(acct.address)
    balance = w3.eth.get_balance(acct.address)
    assert balance == value
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
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    code = w3.eth.get_code(acct.address)
    assert code.hex().startswith("ef0100deadbeef"), "Code was not set!"

    # clear code
    clear_tx = dict(tx)  # copy tx and replace relevant fields
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
    clear_tx_hash = w3.eth.send_raw_transaction(signed_reset.raw_transaction)
    w3.eth.wait_for_transaction_receipt(clear_tx_hash)
    reset_code = w3.eth.get_code(acct.address)
    assert not reset_code.hex().startswith(""), "Code was not set!"
