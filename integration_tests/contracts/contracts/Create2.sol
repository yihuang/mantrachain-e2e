// SPDX-License-Identifier: Unlicense
pragma solidity ^0.8.0;

/**
 * @title Deterministic Deployment Proxy
 * @notice A proxy contract that can be used for deploying contracts to a deterministic address on any chain.
 * @dev This contract uses CREATE2 to deploy contracts with a deterministic address.
 *      The first 32 bytes of calldata should contain the salt, followed by the contract bytecode.
 */
contract Create2 {
    
    /**
     * @notice Event emitted when a contract is deployed
     * @param deployed The address of the deployed contract
     * @param salt The salt used for deployment
     */
    event ContractDeployed(address indexed deployed, bytes32 indexed salt);
    
    /**
     * @notice Receive function to handle plain ETH transfers
     */
    receive() external payable {}
    
    /**
     * @notice Deploys a contract using CREATE2
     * @dev The calldata format should be: [32 bytes salt][contract bytecode]
     *      Returns the address of the deployed contract (packed to 20 bytes starting at offset 12)
     * @return result The deployed contract address (20 bytes starting at memory position 12)
     */
    fallback(bytes calldata /* data */) external payable returns (bytes memory result) {
        // Extract salt from the first 32 bytes of calldata
        bytes32 salt;
        assembly {
            salt := calldataload(0)
        }
        
        // Get the bytecode (everything after the first 32 bytes)
        bytes memory bytecode = new bytes(msg.data.length - 32);
        assembly {
            calldatacopy(add(bytecode, 0x20), 32, sub(calldatasize(), 32))
        }
        
        // Deploy the contract using CREATE2
        address deployed;
        assembly {
            deployed := create2(
                callvalue(),                    // value (ETH to send)
                add(bytecode, 0x20),           // bytecode start
                mload(bytecode),               // bytecode length
                salt                           // salt
            )
            
            // Revert if deployment failed
            if iszero(deployed) {
                revert(0, 0)
            }
            
            // Store the address in memory and return it
            mstore(0, deployed)
            return(12, 20)  // Return 20 bytes starting at position 12 (address)
        }
    }
    
    /**
     * @notice Computes the deterministic address for a contract deployment
     * @param salt The salt to use for deployment
     * @param bytecode The contract bytecode
     * @return The computed address where the contract would be deployed
     */
    function computeAddress(bytes32 salt, bytes memory bytecode) 
        external 
        view 
        returns (address) 
    {
        bytes32 bytecodeHash = keccak256(bytecode);
        bytes32 addressHash = keccak256(
            abi.encodePacked(
                bytes1(0xff),
                address(this),
                salt,
                bytecodeHash
            )
        );
        return address(uint160(uint256(addressHash)));
    }
    
    /**
     * @notice Deploys a contract using CREATE2 (alternative function-based interface)
     * @param salt The salt to use for deployment
     * @param bytecode The contract bytecode
     * @return deployed The address of the deployed contract
     */
    function deploy(bytes32 salt, bytes memory bytecode) 
        external 
        payable 
        returns (address deployed) 
    {
        assembly {
            deployed := create2(
                callvalue(),                    // value (ETH to send)
                add(bytecode, 0x20),           // bytecode start
                mload(bytecode),               // bytecode length
                salt                           // salt
            )
            
            // Revert if deployment failed
            if iszero(deployed) {
                revert(0, 0)
            }
        }
        
        emit ContractDeployed(deployed, salt);
        return deployed;
    }
}
