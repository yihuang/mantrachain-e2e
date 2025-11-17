import asyncio
import json
from pathlib import Path

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_contract.contract import Contract
from eth_contract.utils import get_initcode, send_transaction
from eth_contract.weth import WETH
from eth_utils import to_checksum_address
from web3 import AsyncWeb3

from .utils import (
    ACCOUNTS,
    ADDRS,
    KEYS,
    WETH_ADDRESS,
    build_contract,
    create_contract_transaction,
    w3_wait_for_new_blocks_async,
)

pytestmark = pytest.mark.asyncio


# Safe contract artifacts
SAFE_ARTIFACT = build_contract("Safe_flattened")
SAFE_PROXY_FACTORY_ARTIFACT = build_contract("SafeProxyFactory_flattened")


class SafeManager:
    """Helper class for managing Safe contracts"""

    def __init__(self, w3: AsyncWeb3):
        self.w3 = w3
        self.safe_singleton = None
        self.proxy_factory = None

    async def deploy_safe_singleton(self, account=ACCOUNTS["community"]):
        """Deploy Safe singleton contract"""
        if self.safe_singleton:
            return self.safe_singleton

        receipt = await send_transaction(
            self.w3, account, data=get_initcode(SAFE_ARTIFACT)
        )
        self.safe_singleton = receipt["contractAddress"]
        return self.safe_singleton

    async def deploy_proxy_factory(self, account=ACCOUNTS["community"]):
        """Deploy SafeProxyFactory contract"""
        if self.proxy_factory:
            return self.proxy_factory

        receipt = await send_transaction(
            self.w3, account, data=get_initcode(SAFE_PROXY_FACTORY_ARTIFACT)
        )
        self.proxy_factory = receipt["contractAddress"]
        return self.proxy_factory

    async def create_safe_proxy(
        self,
        owners,
        threshold,
        salt_nonce=0,
        account=ACCOUNTS["community"],
    ):
        """Create a new Safe proxy using the factory"""
        await self.deploy_safe_singleton()
        await self.deploy_proxy_factory()

        # Create initialization data for the Safe
        safe_contract = Contract(SAFE_ARTIFACT["abi"])
        setup_data = safe_contract.fns.setup(
            owners,
            threshold,
            "0x0000000000000000000000000000000000000000",  # to
            b"",  # data
            "0x0000000000000000000000000000000000000000",  # fallbackHandler
            "0x0000000000000000000000000000000000000000",  # paymentToken
            0,  # payment
            "0x0000000000000000000000000000000000000000",  # paymentReceiver
        ).data

        # Create proxy through factory
        factory_contract = Contract(SAFE_PROXY_FACTORY_ARTIFACT["abi"])
        receipt = await factory_contract.fns.createProxyWithNonce(
            self.safe_singleton, setup_data, salt_nonce
        ).transact(self.w3, account, to=self.proxy_factory)

        # Extract proxy address from logs
        proxy_creation_topic = self.w3.keccak(text="ProxyCreation(address,address)")
        for log in receipt["logs"]:
            if log["topics"][0] == proxy_creation_topic:
                proxy_address = to_checksum_address(
                    "0x" + log["topics"][1].hex()[-40:]
                )
                return proxy_address

        raise Exception("Proxy creation event not found")


async def test_safe_deployment(mantra):
    """Test Safe singleton and proxy factory deployment"""
    w3 = mantra.async_w3
    safe_manager = SafeManager(w3)

    # Deploy Safe singleton
    singleton_address = await safe_manager.deploy_safe_singleton()
    assert await w3.eth.get_code(singleton_address)
    print(f"Safe singleton deployed at: {singleton_address}")

    # Deploy proxy factory
    factory_address = await safe_manager.deploy_proxy_factory()
    assert await w3.eth.get_code(factory_address)
    print(f"SafeProxyFactory deployed at: {factory_address}")


async def test_safe_proxy_creation(mantra):
    """Test creating a Safe proxy with multiple owners"""
    w3 = mantra.async_w3
    safe_manager = SafeManager(w3)

    # Define Safe owners and threshold
    owners = [ADDRS["community"], ADDRS["signer1"], ADDRS["signer2"]]
    threshold = 2  # Require 2 out of 3 signatures

    # Create Safe proxy
    safe_address = await safe_manager.create_safe_proxy(owners, threshold)
    assert await w3.eth.get_code(safe_address)
    print(f"Safe proxy deployed at: {safe_address}")

    # Verify Safe configuration
    safe_contract = Contract(SAFE_ARTIFACT["abi"])

    # Check threshold
    actual_threshold = await safe_contract.fns.getThreshold().call(
        w3, to=safe_address
    )
    assert actual_threshold == threshold

    # Check owners
    actual_owners = await safe_contract.fns.getOwners().call(w3, to=safe_address)
    assert set(actual_owners) == set(owners)

    # Verify individual owner status
    for owner in owners:
        is_owner = await safe_contract.fns.isOwner(owner).call(w3, to=safe_address)
        assert is_owner


async def test_safe_transaction_execution(mantra):
    """Test executing a transaction through Safe with multiple signatures"""
    w3 = mantra.async_w3
    safe_manager = SafeManager(w3)

    # Define Safe with 2 out of 3 threshold
    owners = [ADDRS["community"], ADDRS["signer1"], ADDRS["signer2"]]
    threshold = 2

    # Create Safe proxy
    safe_address = await safe_manager.create_safe_proxy(owners, threshold)

    # Fund the Safe
    fund_amount = 10**18  # 1 ETH
    await send_transaction(
        w3, ACCOUNTS["community"], to=safe_address, value=fund_amount
    )
    safe_balance = await w3.eth.get_balance(safe_address)
    assert safe_balance == fund_amount

    # Prepare a simple transfer transaction
    recipient = ADDRS["validator"]
    transfer_amount = 10**17  # 0.1 ETH

    safe_contract = Contract(SAFE_ARTIFACT["abi"])

    # Get transaction hash
    nonce = await safe_contract.fns.nonce().call(w3, to=safe_address)
    tx_hash = await safe_contract.fns.getTransactionHash(
        recipient,
        transfer_amount,
        b"",  # empty data
        0,  # Call operation
        0,  # safeTxGas
        0,  # baseGas
        0,  # gasPrice
        "0x0000000000000000000000000000000000000000",  # gasToken
        "0x0000000000000000000000000000000000000000",  # refundReceiver
        nonce,
    ).call(w3, to=safe_address)

    # Sign transaction with first owner
    message = encode_defunct(primitive=tx_hash)
    signature1 = ACCOUNTS["community"].sign_message(message)

    # Sign transaction with second owner
    signature2 = ACCOUNTS["signer1"].sign_message(message)

    # Combine signatures (sorted by address)
    signatures = b""
    if ACCOUNTS["community"].address < ACCOUNTS["signer1"].address:
        signatures = signature1.signature + signature2.signature
    else:
        signatures = signature2.signature + signature1.signature

    # Execute transaction
    receipt = await safe_contract.fns.execTransaction(
        recipient,
        transfer_amount,
        b"",  # empty data
        0,  # Call operation
        0,  # safeTxGas
        0,  # baseGas
        0,  # gasPrice
        "0x0000000000000000000000000000000000000000",  # gasToken
        "0x0000000000000000000000000000000000000000",  # refundReceiver
        signatures,
    ).transact(w3, ACCOUNTS["community"], to=safe_address)

    assert receipt["status"] == 1

    # Verify funds were transferred
    recipient_balance = await w3.eth.get_balance(recipient)
    assert recipient_balance >= transfer_amount

    # Verify Safe balance decreased
    new_safe_balance = await w3.eth.get_balance(safe_address)
    assert new_safe_balance < safe_balance


async def test_safe_erc20_transfer(mantra):
    """Test Safe executing ERC20 token transfers"""
    w3 = mantra.async_w3
    safe_manager = SafeManager(w3)

    # Deploy WETH for testing
    weth_contract = WETH(to=WETH_ADDRESS)

    # Define Safe with simple 1 out of 1 threshold
    owners = [ADDRS["community"]]
    threshold = 1

    # Create Safe proxy
    safe_address = await safe_manager.create_safe_proxy(owners, threshold)

    # Fund Safe with ETH for gas
    await send_transaction(
        w3, ACCOUNTS["community"], to=safe_address, value=10**18
    )

    # Deposit ETH to WETH for the Safe
    deposit_amount = 10**17  # 0.1 ETH
    await weth_contract.fns.deposit().transact(
        w3, ACCOUNTS["community"], value=deposit_amount
    )

    # Transfer WETH to Safe
    await weth_contract.fns.transfer(safe_address, deposit_amount).transact(
        w3, ACCOUNTS["community"]
    )

    # Verify Safe has WETH
    safe_weth_balance = await weth_contract.fns.balanceOf(safe_address).call(w3)
    assert safe_weth_balance == deposit_amount

    # Prepare ERC20 transfer from Safe
    recipient = ADDRS["signer1"]
    transfer_amount = 5 * 10**16  # 0.05 WETH

    safe_contract = Contract(SAFE_ARTIFACT["abi"])

    # Get transaction hash for ERC20 transfer
    nonce = await safe_contract.fns.nonce().call(w3, to=safe_address)

    # ERC20 transfer data
    transfer_data = weth_contract.fns.transfer(recipient, transfer_amount).data

    tx_hash = await safe_contract.fns.getTransactionHash(
        WETH_ADDRESS,  # to WETH contract
        0,  # value
        transfer_data,
        0,  # Call operation
        0,  # safeTxGas
        0,  # baseGas
        0,  # gasPrice
        "0x0000000000000000000000000000000000000000",  # gasToken
        "0x0000000000000000000000000000000000000000",  # refundReceiver
        nonce,
    ).call(w3, to=safe_address)

    # Sign transaction
    message = encode_defunct(primitive=tx_hash)
    signature = ACCOUNTS["community"].sign_message(message)

    # Execute ERC20 transfer
    receipt = await safe_contract.fns.execTransaction(
        WETH_ADDRESS,  # to WETH contract
        0,  # value
        transfer_data,
        0,  # Call operation
        0,  # safeTxGas
        0,  # baseGas
        0,  # gasPrice
        "0x0000000000000000000000000000000000000000",  # gasToken
        "0x0000000000000000000000000000000000000000",  # refundReceiver
        signature.signature,
    ).transact(w3, ACCOUNTS["community"], to=safe_address)

    assert receipt["status"] == 1

    # Verify WETH was transferred
    recipient_weth_balance = await weth_contract.fns.balanceOf(recipient).call(w3)
    assert recipient_weth_balance == transfer_amount

    # Verify Safe WETH balance decreased
    new_safe_weth_balance = await weth_contract.fns.balanceOf(safe_address).call(w3)
    assert new_safe_weth_balance == deposit_amount - transfer_amount


async def test_safe_owner_management(mantra):
    """Test adding and removing Safe owners"""
    w3 = mantra.async_w3
    safe_manager = SafeManager(w3)

    # Start with single owner
    initial_owners = [ADDRS["community"]]
    threshold = 1

    # Create Safe proxy
    safe_address = await safe_manager.create_safe_proxy(initial_owners, threshold)
    safe_contract = Contract(SAFE_ARTIFACT["abi"])

    # Fund Safe for gas
    await send_transaction(
        w3, ACCOUNTS["community"], to=safe_address, value=10**18
    )

    # Add new owner
    new_owner = ADDRS["signer1"]
    new_threshold = 1

    # Get transaction hash for addOwnerWithThreshold
    nonce = await safe_contract.fns.nonce().call(w3, to=safe_address)
    add_owner_data = safe_contract.fns.addOwnerWithThreshold(
        new_owner, new_threshold
    ).data

    tx_hash = await safe_contract.fns.getTransactionHash(
        safe_address,  # to self
        0,  # value
        add_owner_data,
        0,  # Call operation
        0,  # safeTxGas
        0,  # baseGas
        0,  # gasPrice
        "0x0000000000000000000000000000000000000000",  # gasToken
        "0x0000000000000000000000000000000000000000",  # refundReceiver
        nonce,
    ).call(w3, to=safe_address)

    # Sign transaction
    message = encode_defunct(primitive=tx_hash)
    signature = ACCOUNTS["community"].sign_message(message)

    # Execute owner addition
    receipt = await safe_contract.fns.execTransaction(
        safe_address,  # to self
        0,  # value
        add_owner_data,
        0,  # Call operation
        0,  # safeTxGas
        0,  # baseGas
        0,  # gasPrice
        "0x0000000000000000000000000000000000000000",  # gasToken
        "0x0000000000000000000000000000000000000000",  # refundReceiver
        signature.signature,
    ).transact(w3, ACCOUNTS["community"], to=safe_address)

    assert receipt["status"] == 1

    # Verify new owner was added
    updated_owners = await safe_contract.fns.getOwners().call(w3, to=safe_address)
    assert new_owner in updated_owners
    assert len(updated_owners) == 2

    # Verify new owner status
    is_owner = await safe_contract.fns.isOwner(new_owner).call(w3, to=safe_address)
    assert is_owner


@pytest.mark.connect
async def test_connect_safe_flow(connect_mantra):
    """Test Safe functionality with connect mode"""
    await test_safe_deployment(None, connect_mantra)


async def test_safe_deployment(mantra, connect_mantra):
    """Test Safe deployment and basic functionality"""
    w3 = connect_mantra.async_w3

    # Run all Safe tests
    await test_safe_deployment_logic(w3)
    await test_safe_proxy_creation_logic(w3)
    await test_safe_transaction_execution_logic(w3)


async def test_safe_deployment_logic(w3):
    """Test Safe singleton deployment"""
    safe_manager = SafeManager(w3)
    singleton_address = await safe_manager.deploy_safe_singleton()
    assert await w3.eth.get_code(singleton_address)
    print(f"✓ Safe singleton deployed: {singleton_address}")


async def test_safe_proxy_creation_logic(w3):
    """Test Safe proxy creation"""
    safe_manager = SafeManager(w3)
    owners = [ADDRS["community"], ADDRS["signer1"]]
    threshold = 2

    safe_address = await safe_manager.create_safe_proxy(owners, threshold)
    assert await w3.eth.get_code(safe_address)
    print(f"✓ Safe proxy deployed: {safe_address}")


async def test_safe_transaction_execution_logic(w3):
    """Test Safe transaction execution"""
    safe_manager = SafeManager(w3)
    owners = [ADDRS["community"]]
    threshold = 1

    safe_address = await safe_manager.create_safe_proxy(owners, threshold)

    # Fund and test simple transfer
    await send_transaction(w3, ACCOUNTS["community"], to=safe_address, value=10**17)

    safe_contract = Contract(SAFE_ARTIFACT["abi"])
    nonce = await safe_contract.fns.nonce().call(w3, to=safe_address)

    # Simple transfer to self
    tx_hash = await safe_contract.fns.getTransactionHash(
        ADDRS["community"],
        10**16,
        b"",
        0, 0, 0, 0,
        "0x0000000000000000000000000000000000000000",
        "0x0000000000000000000000000000000000000000",
        nonce,
    ).call(w3, to=safe_address)

    message = encode_defunct(primitive=tx_hash)
    signature = ACCOUNTS["community"].sign_message(message)

    receipt = await safe_contract.fns.execTransaction(
        ADDRS["community"],
        10**16,
        b"",
        0, 0, 0, 0,
        "0x0000000000000000000000000000000000000000",
        "0x0000000000000000000000000000000000000000",
        signature.signature,
    ).transact(w3, ACCOUNTS["community"], to=safe_address)

    assert receipt["status"] == 1
    print("✓ Safe transaction executed successfully")