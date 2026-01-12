from pathlib import Path

import pytest
import web3
from eth_abi import encode
from eth_contract.contract import Contract as ContractAsync
from eth_contract.create2 import create2_address
from eth_contract.deploy_utils import (
    ensure_create2_deployed,
    ensure_deployed_by_create2,
    ensure_multicall3_deployed,
)
from eth_contract.erc20 import ERC20
from eth_contract.multicall3 import multicall
from eth_utils import to_checksum_address

from .utils import ACCOUNTS, ADDRS, retry_on_nonce_mismatch

GAS_PRICE = 1000000000000
WOM = to_checksum_address("0x4200000000000000000000000000000000000006")
ERC20Bin = bytes.fromhex(
    Path(__file__).parent.joinpath("configs/ERC20.bin").read_text()
)
ERC20Salt = bytes.fromhex(
    "636dd1d57837e7dce61901468217da9975548dcb3ecc24d84567feb93cd11e36"
)


# class BankMethod(enum.IntEnum):
#     NAME = 0
#     SYMBOL = 1
#     DECIMALS = 2
#     TOTAL_SUPPLY = 3
#     BALANCE_OF = 4
#     TRANSFER_FROM = 5
#
#     def args(self, *args: Unpack[bytes]) -> bytes:
#         return b"".join([bytes([self.value]), *args])


BANK_PRECOMPILE = to_checksum_address("0x0000000000000000000000000000000000000804")

BANK = ContractAsync.from_abi(
    [
        "function name(string denom) view returns (string)",
        "function symbol(string denom) view returns (string)",
        "function decimals(string denom) view returns (uint8)",
        "function totalSupply(string denom) view returns (uint256)",
        "function balanceOf(address account, string denom) view returns (uint256)",
        """
        function transferFrom(
            address from,
            address to,
            uint256 value,
            string denom
        ) returns (bool)
        """,
    ]
)

TEST_DENOM = "atoken"
EXPECTED_NAME = "Test Coin"
EXPECTED_SYMBOL = "ATOKEN"
EXPECTED_DECIMALS = 18
INITIAL_SUPPLY = 1_000_000_000_000


async def deploy_erc20_wrapper(w3):
    await ensure_create2_deployed(w3, ACCOUNTS["validator"], gasPrice=GAS_PRICE)
    initcode = ERC20Bin + encode(["string", "address"], [TEST_DENOM, BANK_PRECOMPILE])
    token = await ensure_deployed_by_create2(
        w3, ACCOUNTS["validator"], initcode, ERC20Salt, gasPrice=GAS_PRICE
    )
    return token, initcode


# @pytest.mark.asyncio
# async def test_bank_precompile(mantra):
#     """Old test for bank precompile at 0x807 with byte-based ABI."""
#     w3 = mantra.async_w3
#     await ensure_multicall3_deployed(w3, ACCOUNTS["validator"], gasPrice=GAS_PRICE)
#
#     bank = to_checksum_address("0x0000000000000000000000000000000000000807")
#     user = ADDRS["community"]
#     denom = "atoken"
#     calls = [
#         Call3(bank, data=BankMethod.NAME.args(denom.encode())),
#         Call3(bank, data=BankMethod.SYMBOL.args(denom.encode())),
#         Call3(bank, data=BankMethod.DECIMALS.args(denom.encode())),
#         Call3(bank, data=BankMethod.TOTAL_SUPPLY.args(denom.encode())),
#         Call3(
#             bank,
#             data=BankMethod.BALANCE_OF.args(to_bytes(hexstr=user), denom.encode()),
#         ),
#     ]
#     results = await MULTICALL3.fns.aggregate3(calls).call(w3)
#     expected = (
#         (True, b"Test Coin"),
#         (True, b"ATOKEN"),
#         (True, bytes([18])),
#         (True, (1000000000000).to_bytes(32, "big")),
#         (True, (1000000000000).to_bytes(32, "big")),
#     )
#     assert expected == results
#
#     # owner can transfer funds on bank precompile directly
#     recipient = ADDRS["validator"]
#     amount = 1000
#     data = BankMethod.TRANSFER_FROM.args(
#         to_bytes(hexstr=user),
#         to_bytes(hexstr=recipient),
#         amount.to_bytes(32, "big"),
#         denom.encode(),
#     )
#     await send_transaction(
#         w3, ACCOUNTS["community"], to=bank, data=data, gasPrice=GAS_PRICE
#     )
#
#     with pytest.raises(web3.exceptions.ContractLogicError):
#         # wrong user fail
#         await send_transaction(
#             w3, ACCOUNTS["validator"], to=bank, data=data, gasPrice=GAS_PRICE
#         )


# @pytest.mark.asyncio
# async def test_bank_erc20(mantra):
#     """Old test for ERC20 wrapper with bank precompile at 0x807."""
#     w3 = mantra.async_w3
#     await ensure_create2_deployed(w3, ACCOUNTS["validator"], gasPrice=GAS_PRICE)
#     await ensure_multicall3_deployed(w3, ACCOUNTS["validator"], gasPrice=GAS_PRICE)
#
#     bank = to_checksum_address("0x0000000000000000000000000000000000000807")
#     user = ADDRS["community"]
#     denom = "atoken"
#
#     initcode = ERC20Bin + encode(["string", "address"], [denom, bank])
#     token = await create2_deploy(
#         w3, ACCOUNTS["validator"], initcode, ERC20Salt, gasPrice=GAS_PRICE
#     )
#
#     test_user = to_checksum_address(b"\x01" * 20)
#     await ERC20.fns.transfer(test_user, 1).transact(
#         w3, ACCOUNTS["community"], to=token, gasPrice=GAS_PRICE
#     )
#
#     expected = ["Test Coin", "ATOKEN", 18, 1000000000000, 1]
#     calls = [
#         (token, ERC20.fns.name()),
#         (token, ERC20.fns.symbol()),
#         (token, ERC20.fns.decimals()),
#         (token, ERC20.fns.totalSupply()),
#         (token, ERC20.fns.balanceOf(test_user)),
#     ]
#     result = await multicall(w3, calls)
#     assert expected == result
#
#     recipient = ADDRS["validator"]
#     amount = 1000
#     before = (
#         await ERC20.fns.balanceOf(user).call(w3, to=token),
#         await ERC20.fns.balanceOf(recipient).call(w3, to=token),
#     )
#     await ERC20.fns.transfer(recipient, amount).transact(
#         w3, ACCOUNTS["community"], to=token, gasPrice=GAS_PRICE
#     )
#     after = (
#         await ERC20.fns.balanceOf(user).call(w3, to=token),
#         await ERC20.fns.balanceOf(recipient).call(w3, to=token),
#     )
#     assert after == (before[0] - amount, before[1] + amount)


async def test_metadata_for_registered_denom(mantra):
    w3 = mantra.async_w3
    await ensure_multicall3_deployed(w3, ACCOUNTS["validator"], gasPrice=GAS_PRICE)

    calls = [
        (BANK_PRECOMPILE, BANK.fns.name(TEST_DENOM)),
        (BANK_PRECOMPILE, BANK.fns.symbol(TEST_DENOM)),
        (BANK_PRECOMPILE, BANK.fns.decimals(TEST_DENOM)),
    ]
    name, symbol, decimals = await multicall(w3, calls)

    assert name == EXPECTED_NAME
    assert symbol == EXPECTED_SYMBOL
    assert decimals == EXPECTED_DECIMALS


async def test_metadata_for_unregistered_denom(mantra):
    w3 = mantra.async_w3
    unknown_denom = "unknowndenom"

    with pytest.raises(web3.exceptions.ContractLogicError):
        await BANK.fns.name(unknown_denom).call(w3, to=BANK_PRECOMPILE)


async def test_total_supply(mantra):
    w3 = mantra.async_w3
    supply = await BANK.fns.totalSupply(TEST_DENOM).call(w3, to=BANK_PRECOMPILE)
    assert supply == INITIAL_SUPPLY


@pytest.mark.parametrize(
    "user_key,expected_balance",
    [
        ("community", INITIAL_SUPPLY),
        ("validator", 0),
    ],
)
async def test_balance_of(mantra, user_key, expected_balance):
    w3 = mantra.async_w3
    user = ADDRS[user_key]
    balance = await BANK.fns.balanceOf(user, TEST_DENOM).call(w3, to=BANK_PRECOMPILE)
    assert balance == expected_balance


# Authorization rules for bank precompile transferFrom:
# 1. msg.sender == from: User can move their own funds for any denom.
async def test_self_transfer(mantra):
    # msg.sender can transfer their own funds
    w3 = mantra.async_w3
    user = ADDRS["community"]
    recipient = ADDRS["validator"]
    amount = 1_000

    balance_before = await BANK.fns.balanceOf(recipient, TEST_DENOM).call(
        w3, to=BANK_PRECOMPILE
    )
    receipt = await BANK.fns.transferFrom(user, recipient, amount, TEST_DENOM).transact(
        w3, ACCOUNTS["community"], to=BANK_PRECOMPILE, gasPrice=GAS_PRICE
    )
    assert receipt.status == 1, "self transfer should succeed"

    balance_after = await BANK.fns.balanceOf(recipient, TEST_DENOM).call(
        w3, to=BANK_PRECOMPILE
    )
    assert balance_after == balance_before + amount


async def test_unauthorized_transfer_fails(mantra):
    # Non-owner, non-wrapper cannot move someone else's funds.
    w3 = mantra.async_w3
    victim = ADDRS["community"]
    recipient = ADDRS["validator"]
    amount = 1_000

    with pytest.raises(web3.exceptions.ContractLogicError):
        await BANK.fns.transferFrom(victim, recipient, amount, TEST_DENOM).transact(
            w3, ACCOUNTS["validator"], to=BANK_PRECOMPILE, gasPrice=GAS_PRICE
        )


# 2. wrapper is the deterministic authorized contract for its denom
# and can call bank transferFrom on behalf of users.
async def test_deploy_erc20_wrapper(mantra):
    w3 = mantra.async_w3
    token_addr, initcode = await deploy_erc20_wrapper(w3)
    code = await w3.eth.get_code(token_addr)
    assert code, "ERC20 wrapper should be deployed"
    expected_addr = create2_address(initcode, ERC20Salt)
    assert token_addr == expected_addr


# msg.sender is the deterministic ERC20 wrapper for that denom
async def test_erc20_metadata_via_wrapper(mantra):
    w3 = mantra.async_w3
    token, _ = await deploy_erc20_wrapper(w3)
    await ensure_multicall3_deployed(w3, ACCOUNTS["validator"], gasPrice=GAS_PRICE)
    calls = [
        (token, ERC20.fns.name()),
        (token, ERC20.fns.symbol()),
        (token, ERC20.fns.decimals()),
        (token, ERC20.fns.totalSupply()),
    ]
    name, symbol, decimals, supply = await multicall(w3, calls)
    assert name == EXPECTED_NAME
    assert symbol == EXPECTED_SYMBOL
    assert decimals == EXPECTED_DECIMALS
    assert supply == INITIAL_SUPPLY


async def test_erc20_balance_via_wrapper(mantra):
    w3 = mantra.async_w3
    token, _ = await deploy_erc20_wrapper(w3)
    user = ADDRS["community"]
    balance = await ERC20.fns.balanceOf(user).call(w3, to=token)
    assert balance > 0  # may be < INITIAL_SUPPLY due to earlier tests


async def test_erc20_transfer(mantra):
    w3 = mantra.async_w3
    token, _ = await deploy_erc20_wrapper(w3)
    sender = ADDRS["community"]
    recipient = ADDRS["validator"]
    amount = 5_000
    sender_before = await ERC20.fns.balanceOf(sender).call(w3, to=token)
    recipient_before = await ERC20.fns.balanceOf(recipient).call(w3, to=token)
    receipt = await ERC20.fns.transfer(recipient, amount).transact(
        w3, ACCOUNTS["community"], to=token, gasPrice=GAS_PRICE
    )
    assert receipt.status == 1
    sender_after = await ERC20.fns.balanceOf(sender).call(w3, to=token)
    recipient_after = await ERC20.fns.balanceOf(recipient).call(w3, to=token)
    assert sender_after == sender_before - amount
    assert recipient_after == recipient_before + amount


# Allowance is tracked in the wrapper; after checking it, the wrapper
# calls the bank precompile transferFrom.
async def test_erc20_approve_and_transfer_from(mantra):
    w3 = mantra.async_w3
    token, _ = await deploy_erc20_wrapper(w3)
    owner = ADDRS["community"]
    spender = ACCOUNTS["signer1"]
    spender_addr = ADDRS["signer1"]
    recipient = ADDRS["validator"]
    approve_amount = 10_000
    transfer_amount = 5_000

    receipt = await ERC20.fns.approve(spender_addr, approve_amount).transact(
        w3, ACCOUNTS["community"], to=token, gasPrice=GAS_PRICE
    )
    assert receipt.status == 1

    allowance = await ERC20.fns.allowance(owner, spender_addr).call(w3, to=token)
    assert allowance == approve_amount

    owner_before = await ERC20.fns.balanceOf(owner).call(w3, to=token)
    recipient_before = await ERC20.fns.balanceOf(recipient).call(w3, to=token)

    receipt = await retry_on_nonce_mismatch(
        ERC20.fns.transferFrom(owner, recipient, transfer_amount).transact,
        w3,
        spender,
        to=token,
        gasPrice=GAS_PRICE,
    )
    assert receipt.status == 1

    owner_after = await ERC20.fns.balanceOf(owner).call(w3, to=token)
    recipient_after = await ERC20.fns.balanceOf(recipient).call(w3, to=token)

    assert owner_after == owner_before - transfer_amount
    assert recipient_after == recipient_before + transfer_amount

    allowance_after = await ERC20.fns.allowance(owner, spender_addr).call(w3, to=token)
    assert allowance_after == approve_amount - transfer_amount


async def test_erc20_transfer_from_without_allowance_fails(mantra):
    w3 = mantra.async_w3
    token, _ = await deploy_erc20_wrapper(w3)

    owner = ADDRS["community"]
    spender = ACCOUNTS["signer2"]  # has no allowance
    recipient = ADDRS["validator"]
    transfer_amount = 5_000

    with pytest.raises(web3.exceptions.ContractLogicError):
        await ERC20.fns.transferFrom(owner, recipient, transfer_amount).transact(
            w3, spender, to=token, gasPrice=GAS_PRICE
        )


async def test_transfer_event(mantra):
    w3 = mantra.async_w3
    token, _ = await deploy_erc20_wrapper(w3)

    sender = ADDRS["community"]
    recipient = ADDRS["validator"]
    amount = 1_000

    receipt = await ERC20.fns.transfer(recipient, amount).transact(
        w3, ACCOUNTS["community"], to=token, gasPrice=GAS_PRICE
    )

    transfer_logs = [
        log
        for log in receipt.logs
        if log.topics[0].hex() == ERC20.events.Transfer.topic.hex()
    ]
    assert len(transfer_logs) == 1

    transfer_log = transfer_logs[0]
    from_addr = to_checksum_address("0x" + transfer_log.topics[1].hex()[-40:])
    to_addr = to_checksum_address("0x" + transfer_log.topics[2].hex()[-40:])
    logged_amount = int.from_bytes(transfer_log.data, "big")

    assert from_addr == sender
    assert to_addr == recipient
    assert logged_amount == amount


async def test_approval_event(mantra):
    w3 = mantra.async_w3
    token, _ = await deploy_erc20_wrapper(w3)

    owner = ADDRS["community"]
    spender = ADDRS["signer1"]
    amount = 5_000

    receipt = await ERC20.fns.approve(spender, amount).transact(
        w3, ACCOUNTS["community"], to=token, gasPrice=GAS_PRICE
    )

    approval_logs = [
        log
        for log in receipt.logs
        if log.topics[0].hex() == ERC20.events.Approval.topic.hex()
    ]
    assert len(approval_logs) == 1

    approval_log = approval_logs[0]
    owner_addr = to_checksum_address("0x" + approval_log.topics[1].hex()[-40:])
    spender_addr = to_checksum_address("0x" + approval_log.topics[2].hex()[-40:])
    logged_amount = int.from_bytes(approval_log.data, "big")

    assert owner_addr == owner
    assert spender_addr == spender
    assert logged_amount == amount
