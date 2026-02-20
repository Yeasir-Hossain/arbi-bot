// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * TestToken - ERC20 token for testing AI trading strategies
 * 
 * Features:
 * - Mintable by anyone (for testing purposes only!)
 * - Initial supply minted to deployer
 * 
 * ⚠️ DO NOT USE IN PRODUCTION - This is for testing only!
 */
contract TestToken is ERC20 {
    uint8 private _decimals;

    /**
     * @dev Constructor to create a test token
     * @param name Token name
     * @param symbol Token symbol
     * @param initialSupply Initial supply to mint to deployer
     * @param tokenDecimals Number of decimals (default 18)
     */
    constructor(
        string memory name,
        string memory symbol,
        uint256 initialSupply,
        uint8 tokenDecimals
    ) ERC20(name, symbol) {
        _decimals = tokenDecimals;
        _mint(msg.sender, initialSupply * (10 ** tokenDecimals));
    }

    /**
     * @dev Allow anyone to mint tokens (TESTING ONLY!)
     * @param to Address to mint tokens to
     * @param amount Amount of tokens to mint
     */
    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }

    /**
     * @dev Override decimals to use custom value
     */
    function decimals() public view override returns (uint8) {
        return _decimals;
    }
}
