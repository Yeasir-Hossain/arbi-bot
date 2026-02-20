// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * SimpleDEX - Decentralized Exchange for testing AI trading
 * 
 * Features:
 * - Token swapping (constant product AMM)
 * - Liquidity provision
 * - Price oracle
 * 
 * ⚠️ SIMPLIFIED FOR TESTING - Not production ready!
 */
contract SimpleDEX {
    IERC20 public immutable tokenA;
    IERC20 public immutable tokenB;
    
    uint256 public reserveA;
    uint256 public reserveB;
    
    // Events
    event Swap(
        address indexed user,
        uint256 amountIn,
        uint256 amountOut,
        bool isAtoB
    );
    
    event LiquidityAdded(
        address indexed provider,
        uint256 amountA,
        uint256 amountB
    );
    
    event LiquidityRemoved(
        address indexed provider,
        uint256 amountA,
        uint256 amountB
    );

    /**
     * @dev Constructor
     * @param _tokenA Address of token A
     * @param _tokenB Address of token B
     */
    constructor(address _tokenA, address _tokenB) {
        require(_tokenA != address(0), "Invalid token A");
        require(_tokenB != address(0), "Invalid token B");
        require(_tokenA != _tokenB, "Tokens must be different");
        
        tokenA = IERC20(_tokenA);
        tokenB = IERC20(_tokenB);
    }

    /**
     * @dev Add liquidity to the DEX
     * @param amountA Amount of token A to add
     * @param amountB Amount of token B to add
     */
    function addLiquidity(uint256 amountA, uint256 amountB) external {
        require(amountA > 0 && amountB > 0, "Amounts must be > 0");
        
        // Transfer tokens to DEX
        tokenA.transferFrom(msg.sender, address(this), amountA);
        tokenB.transferFrom(msg.sender, address(this), amountB);
        
        // Update reserves
        reserveA += amountA;
        reserveB += amountB;
        
        emit LiquidityAdded(msg.sender, amountA, amountB);
    }

    /**
     * @dev Swap token A for token B
     * @param amountIn Amount of token A to swap
     * @return amountOut Amount of token B received
     */
    function swapAforB(uint256 amountIn) external returns (uint256 amountOut) {
        require(amountIn > 0, "Amount must be > 0");
        require(reserveB > 0, "Insufficient liquidity");
        
        amountOut = getAmountOut(amountIn, reserveA, reserveB);
        
        // Transfer tokens
        tokenA.transferFrom(msg.sender, address(this), amountIn);
        tokenB.transfer(msg.sender, amountOut);
        
        // Update reserves
        reserveA += amountIn;
        reserveB -= amountOut;
        
        emit Swap(msg.sender, amountIn, amountOut, true);
    }

    /**
     * @dev Swap token B for token A
     * @param amountIn Amount of token B to swap
     * @return amountOut Amount of token A received
     */
    function swapBforA(uint256 amountIn) external returns (uint256 amountOut) {
        require(amountIn > 0, "Amount must be > 0");
        require(reserveA > 0, "Insufficient liquidity");
        
        amountOut = getAmountOut(amountIn, reserveB, reserveA);
        
        // Transfer tokens
        tokenB.transferFrom(msg.sender, address(this), amountIn);
        tokenA.transfer(msg.sender, amountOut);
        
        // Update reserves
        reserveB += amountIn;
        reserveA -= amountOut;
        
        emit Swap(msg.sender, amountIn, amountOut, false);
    }

    /**
     * @dev Calculate output amount for a swap
     * @param amountIn Input amount
     * @param reserveIn Reserve of input token
     * @param reserveOut Reserve of output token
     * @return amountOut Output amount (with 0.3% fee)
     */
    function getAmountOut(
        uint256 amountIn,
        uint256 reserveIn,
        uint256 reserveOut
    ) public pure returns (uint256 amountOut) {
        require(amountIn > 0, "Insufficient input amount");
        require(reserveIn > 0 && reserveOut > 0, "Insufficient liquidity");
        
        // Constant product formula with 0.3% fee
        uint256 amountInWithFee = amountIn * 997;
        uint256 numerator = amountInWithFee * reserveOut;
        uint256 denominator = (reserveIn * 1000) + amountInWithFee;
        
        amountOut = numerator / denominator;
    }

    /**
     * @dev Get current price (token A per token B)
     * @return price Price with 18 decimals precision
     */
    function getPrice() external view returns (uint256 price) {
        require(reserveB > 0, "No liquidity");
        return (reserveA * 1e18) / reserveB;
    }

    /**
     * @dev Get reserves
     * @return reserveA Reserve of token A
     * @return reserveB Reserve of token B
     */
    function getReserves() external view returns (uint256, uint256) {
        return (reserveA, reserveB);
    }

    /**
     * @dev Get token addresses
     * @return addressA Token A address
     * @return addressB Token B address
     */
    function getTokenAddresses() external view returns (address, address) {
        return (address(tokenA), address(tokenB));
    }
}
