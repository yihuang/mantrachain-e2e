from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from web3 import Web3

from .utils import (
    ADDRS,
    adjust_base_fee,
    send_transaction,
    w3_wait_for_block,
    w3_wait_for_new_blocks,
)

NEW_BASE_FEE = 100000000000


@pytest.mark.skip(reason="skipping basic")
def test_basic(mantra):
    w3: Web3 = mantra.w3
    # need at least 5 blocks
    w3_wait_for_block(w3, 5)
    call = w3.provider.make_request
    tx = {"to": ADDRS["community"], "value": 10, "gasPrice": w3.eth.gas_price}
    send_transaction(w3, tx)
    size = 4
    # size of base fee + next fee
    max = size + 1
    # only 1 base fee + next fee
    min = 2
    method = "eth_feeHistory"
    field = "baseFeePerGas"
    percentiles = [100]
    height = w3.eth.block_number
    latest = dict(
        blocks=["latest", hex(height)],
        expect=max,
    )
    earliest = dict(
        blocks=["earliest", "0x0"],
        expect=min,
    )
    for tc in [latest, earliest]:
        res = []
        with ThreadPoolExecutor(len(tc["blocks"])) as exec:
            tasks = [
                exec.submit(call, method, [size, b, percentiles]) for b in tc["blocks"]
            ]
            res = [future.result()["result"][field] for future in as_completed(tasks)]
        assert len(res) == len(tc["blocks"])
        assert res[0] == res[1]
        assert len(res[0]) == tc["expect"]

    for x in range(max):
        i = x + 1
        fee_history = call(method, [size, hex(i), percentiles])
        # start to reduce diff on i <= size - min
        diff = size - min - i
        reduce = size - diff
        target = reduce if diff >= 0 else max
        res = fee_history["result"]
        assert len(res[field]) == target
        oldest = i + min - max
        assert res["oldestBlock"] == hex(oldest if oldest > 0 else 0)


@pytest.mark.skip(reason="skipping change")
def test_change(mantra):
    w3: Web3 = mantra.w3
    call = w3.provider.make_request
    tx = {"to": ADDRS["community"], "value": 10, "gasPrice": w3.eth.gas_price}
    send_transaction(w3, tx)
    size = 4
    method = "eth_feeHistory"
    field = "baseFeePerGas"
    percentiles = [100]
    for b in ["latest", hex(w3.eth.block_number)]:
        history0 = call(method, [size, b, percentiles])["result"][field]
        w3_wait_for_new_blocks(w3, 2, 0.1)
        history1 = call(method, [size, b, percentiles])["result"][field]
        if b == "latest":
            assert history1 != history0
        else:
            assert history1 == history0


@pytest.mark.skip(reason="skipping next")
def test_next(mantra):
    w3: Web3 = mantra.w3
    call = w3.provider.make_request
    tx = {"to": ADDRS["community"], "value": 10, "gasPrice": w3.eth.gas_price}
    send_transaction(w3, tx)
    params = mantra.cosmos_cli().get_params("feemarket")
    assert_histories(w3, call, w3.eth.block_number, params, percentiles=[100])


@pytest.mark.skip(reason="skipping beyond head")
def test_beyond_head(mantra):
    end = hex(0x7FFFFFFFFFFFFFFF)
    res = mantra.w3.provider.make_request("eth_feeHistory", [4, end, []])
    msg = f"request beyond head block: requested {int(end, 16)}"
    assert msg in res["error"]["message"]


@pytest.mark.skip(reason="skipping percentiles")
def test_percentiles(mantra):
    w3: Web3 = mantra.w3
    call = w3.provider.make_request
    method = "eth_feeHistory"
    percentiles = [[-1], [101], [2, 1]]
    size = 4
    msg = "invalid reward percentile"
    with ThreadPoolExecutor(len(percentiles)) as exec:
        tasks = [exec.submit(call, method, [size, "latest", p]) for p in percentiles]
        result = [future.result() for future in as_completed(tasks)]
        assert all(msg in res["error"]["message"] for res in result)


def assert_histories(w3, call, blk, params, percentiles=[]):
    method = "eth_feeHistory"
    field = "baseFeePerGas"
    expected = []
    blocks = []
    histories = []
    for i in range(3):
        b = blk + i
        blocks.append(b)
        history = tuple(call(method, [1, hex(b), percentiles])["result"][field])
        histories.append(history)
        w3_wait_for_new_blocks(w3, 1, 0.1)
    blocks.append(b + 1)

    for b in blocks:
        next_base_price = w3.eth.get_block(b).baseFeePerGas
        prev = b - 1
        blk = w3.eth.get_block(prev)
        base_fee = blk.baseFeePerGas
        res = adjust_base_fee(
            base_fee,
            blk.gasLimit,
            blk.gasUsed,
            params,
        )
        if abs(next_base_price - res) == 1:
            next_base_price = res
        elif next_base_price != NEW_BASE_FEE:
            assert next_base_price == res
        expected.append(hex(next_base_price))
    assert histories == list(zip(expected, expected[1:]))
