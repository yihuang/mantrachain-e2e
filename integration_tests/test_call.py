import base64
import io
import json
from contextlib import redirect_stdout
from typing import Iterable, Unpack

import aiohttp
import pyrevm
import pytest
from cprotobuf import Field, ProtoEntity
from eth_contract.erc20 import ERC20
from eth_contract.slots import parse_balance_slot
from eth_contract.utils import ZERO_ADDRESS
from hexbytes import HexBytes
from pystarport import ports
from web3 import Web3
from web3._utils.contracts import encode_transaction_data
from web3.types import TxParams

from .utils import (
    ADDRS,
    WETH_ADDRESS,
    Greeter,
    assert_create_erc20_denom,
    assert_create_tokenfactory_denom,
    assert_mint_tokenfactory_denom,
    build_and_deploy_contract_async,
    denom_to_erc20_address,
)


def test_temporary_contract_code(mantra):
    state = 100
    w3: Web3 = mantra.w3
    greeter = Greeter("Greeter")
    data = encode_transaction_data(w3, "intValue", greeter.abi, args=[], kwargs={})
    # call an arbitrary address
    address = w3.to_checksum_address("0x0000000000000000000000000000ffffffffffff")
    hex_state = f"0x{HexBytes(w3.codec.encode(('uint256',), (state,))).hex()}"
    overrides = {
        address: {
            "code": greeter.code,
            "state": {
                ("0x" + "0" * 64): hex_state,
            },
        },
    }
    result = w3.eth.call(
        {
            "to": address,
            "data": data,
        },
        "latest",
        overrides,
    )
    assert (state,) == w3.codec.decode(("uint256",), result)


def test_override_state(mantra):
    w3: Web3 = mantra.w3
    greeter = Greeter("Greeter")
    greeter.deploy(w3)
    contract = greeter.contract
    assert "Hello" == contract.functions.greet().call()
    assert 0 == contract.functions.intValue().call()

    int_value = 100
    hex_state = f"0x{HexBytes(w3.codec.encode(('uint256',), (int_value,))).hex()}"
    state = {
        ("0x" + "0" * 64): hex_state,
    }
    data = encode_transaction_data(w3, "intValue", greeter.abi, args=[], kwargs={})
    result = w3.eth.call(
        {
            "to": contract.address,
            "data": data,
        },
        "latest",
        {
            contract.address: {
                "code": greeter.code,
                "stateDiff": state,
            },
        },
    )
    assert (int_value,) == w3.codec.decode(("uint256",), result)

    # stateDiff don't affect the other state slots
    data = encode_transaction_data(w3, "greet", greeter.abi, args=[], kwargs={})
    result = w3.eth.call(
        {
            "to": contract.address,
            "data": data,
        },
        "latest",
        {
            contract.address: {
                "to": contract.address,
                "stateDiff": state,
            },
        },
    )
    assert ("Hello",) == w3.codec.decode(("string",), result)

    # state will overrides the whole state
    data = encode_transaction_data(w3, "greet", greeter.abi, args=[], kwargs={})
    result = w3.eth.call(
        {
            "to": contract.address,
            "data": data,
        },
        "latest",
        {
            contract.address: {
                "to": contract.address,
                "state": state,
            },
        },
    )
    assert ("",) == w3.codec.decode(("string",), result)


def trace_call(vm: pyrevm.EVM, **tx: Unpack[TxParams]) -> Iterable[dict]:
    """
    Capture and parse traces from a pyrevm message call.
    """
    with redirect_stdout(io.StringIO()) as out:
        vm.message_call(
            caller=tx.get("from", ZERO_ADDRESS),
            to=tx.get("to", ""),
            calldata=tx.get("data"),
            value=tx.get("value", 0),
        )

    out.seek(0)
    for line in out.readlines():
        yield json.loads(line)


@pytest.mark.asyncio
async def test_override_erc20_state(mantra):
    w3 = mantra.async_w3
    community = ADDRS["community"]
    _, total = await assert_create_erc20_denom(w3, community)
    int_value = total - 1

    fn = ERC20.fns.balanceOf(community)
    vm = pyrevm.EVM(fork_url=mantra.w3_http_endpoint(), tracing=True, with_memory=True)
    traces = trace_call(vm, to=WETH_ADDRESS, data=fn.data)
    fn_slot = parse_balance_slot(HexBytes(WETH_ADDRESS), HexBytes(community), traces)
    state_key = f"0x{fn_slot.value(HexBytes(community)).slot.hex()}"
    hex_state = "0x" + HexBytes(w3.codec.encode(("uint256",), (int_value,))).hex()

    state = {state_key: hex_state}

    for state_type in ["stateDiff", "state"]:
        res = await w3.eth.call(
            {"to": WETH_ADDRESS, "data": fn.data},
            "latest",
            {WETH_ADDRESS: {state_type: state}},
        )
        assert fn.decode(res) == int_value


class StateEntry(ProtoEntity):
    key = Field("bytes", 1)
    value = Field("bytes", 2)
    delete = Field("bool", 3)


class StoreStateDiff(ProtoEntity):
    name = Field("string", 1)
    entries = Field(StateEntry, 2, repeated=True)


def create_bank_balance_key(addr_bytes, denom):
    balances_prefix = bytes([2])
    addr_len = bytes([len(addr_bytes)])
    # prefix + addr_len + addr + denom
    return balances_prefix + addr_len + addr_bytes + denom.encode("utf-8")


@pytest.mark.asyncio
@pytest.mark.skip(reason="skipping test_override_precompile_state")
async def test_override_precompile_state(mantra):
    w3 = mantra.async_w3
    cli = mantra.cosmos_cli()
    community = ADDRS["community"]
    sender = cli.address("community")
    subdenom = "eth_call"
    amt = 10**6
    denom = assert_create_tokenfactory_denom(cli, subdenom, _from=sender, gas=620000)
    tf_erc20_addr = denom_to_erc20_address(denom)
    assert_mint_tokenfactory_denom(cli, denom, amt, _from=sender, gas=300000)

    balance = cli.balance(sender, denom)
    balance_eth = await ERC20.fns.balanceOf(community).call(w3, to=tf_erc20_addr)
    total = await ERC20.fns.totalSupply().call(w3, to=tf_erc20_addr)
    assert balance == balance_eth == total == amt

    int_value = 99
    fn = ERC20.fns.balanceOf(community)

    addr_bytes = bytes.fromhex(community[2:])
    key = create_bank_balance_key(addr_bytes, denom)
    value = str(int_value).encode("utf-8")
    cosmos_overrides = {
        "cosmosStateOverrides": [
            {
                "name": "bank",
                "entries": [
                    {
                        "key": base64.b64encode(key).decode(),
                        "value": base64.b64encode(value).decode(),
                        "delete": False,
                    }
                ],
            }
        ]
    }
    rpc_url = f"http://127.0.0.1:{ports.evmrpc_port(mantra.base_port(0))}"
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [
            {
                "to": tf_erc20_addr,
                "data": "0x" + fn.data.hex(),
            },
            "latest",
            cosmos_overrides,
        ],
        "id": 1,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(rpc_url, json=payload) as response:
            result = await response.json()
            if "error" in result:
                raise Exception(f"RPC error: {result['error']}")

            res_hex = result["result"]
            res_bytes = bytes.fromhex(res_hex[2:])
            assert fn.decode(res_bytes) == int_value


@pytest.mark.connect
async def test_connect_opcode(connect_mantra):
    await test_opcode(None, connect_mantra)


@pytest.mark.asyncio
async def test_opcode(mantra, connect_mantra):
    contract = await build_and_deploy_contract_async(connect_mantra.async_w3, "Random")
    res = await contract.caller.randomTokenId()
    assert res > 0, res
