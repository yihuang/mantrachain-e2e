import pytest

from .utils import (
    ADDRS,
    KEYS,
    derive_new_account,
    send_transaction,
    w3_wait_for_new_blocks,
)


@pytest.mark.connect
def test_connect_get_transaction_count(connect_mantra):
    get_transaction_count(connect_mantra)


def test_get_transaction_count(mantra):
    get_transaction_count(mantra)


def get_transaction_count(mantra):
    w3 = mantra.w3
    blk = hex(w3.eth.block_number)
    name = "community"
    sender = ADDRS[name]
    receiver = derive_new_account().address
    n0 = w3.eth.get_transaction_count(receiver, blk)
    # ensure transaction send in new block
    w3_wait_for_new_blocks(w3, 1, sleep=0.1)
    receipt = send_transaction(
        w3,
        {
            "from": sender,
            "to": receiver,
            "value": 1000,
        },
        KEYS[name],
    )
    assert receipt.status == 1
    [n1, n2] = [w3.eth.get_transaction_count(receiver, b) for b in [blk, "latest"]]
    assert n0 == n1
    assert n0 == n2


@pytest.mark.connect
def test_connect_query_future_blk(connect_mantra):
    query_future_blk(connect_mantra)


def test_query_future_blk(mantra):
    query_future_blk(mantra)


def query_future_blk(mantra):
    w3 = mantra.w3
    acc = derive_new_account(2).address
    current = w3.eth.block_number
    future = current + 1000
    with pytest.raises(ValueError) as exc:
        w3.eth.get_transaction_count(acc, hex(future))
    assert "cannot query with height in the future" in str(exc)
