import pytest

from .utils import (
    ADDRS,
    CONTRACTS,
    KEYS,
    deploy_contract_with_receipt,
    send_transaction,
    w3_wait_for_new_blocks,
)


def test_gas_call(mantra):
    function_input = 10
    mantra_contract, _ = deploy_contract_with_receipt(mantra.w3, CONTRACTS["BurnGas"])
    mantra_txhash = mantra_contract.functions.burnGas(function_input).transact(
        {"from": ADDRS["validator"], "gasPrice": mantra.w3.eth.gas_price}
    )
    mantra_call_receipt = mantra.w3.eth.wait_for_transaction_receipt(mantra_txhash)
    assert mantra_call_receipt.gasUsed == 267426


def test_block_gas_limit(mantra):
    tx_value = 10

    # get the block gas limit from the latest block
    w3_wait_for_new_blocks(mantra.w3, 5)
    block = mantra.w3.eth.get_block("latest")
    exceeded_gas_limit = block.gasLimit + 100

    # send a transaction exceeding the block gas limit
    mantra_gas_price = mantra.w3.eth.gas_price
    tx = {
        "to": ADDRS["community"],
        "value": tx_value,
        "gas": exceeded_gas_limit,
        "gasPrice": mantra_gas_price,
    }

    # expect an error due to the block gas limit
    with pytest.raises(Exception):
        send_transaction(mantra.w3, tx, KEYS["validator"])

    # deploy a contract on mantra
    mantra_contract, _ = deploy_contract_with_receipt(mantra.w3, CONTRACTS["BurnGas"])

    # expect an error on contract call due to block gas limit
    with pytest.raises(Exception):
        mantra_txhash = mantra_contract.functions.burnGas(exceeded_gas_limit).transact(
            {
                "from": ADDRS["validator"],
                "gas": exceeded_gas_limit,
                "gasPrice": mantra_gas_price,
            }
        )
        (mantra.w3.eth.wait_for_transaction_receipt(mantra_txhash))
