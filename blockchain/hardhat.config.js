require("@nomicfoundation/hardhat-toolbox");

/**
 * Hardhat Configuration for AI Trading System
 * 
 * This sets up a local Ethereum blockchain for testing AI trading strategies
 * without risking real money.
 */

module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  
  networks: {
    hardhat: {
      chainId: 1337,
      mining: {
        auto: true,
        interval: 1000  // Mine block every second
      },
      accounts: {
        count: 10,
        accountsBalance: "10000000000000000000000" // 10,000 ETH each
      }
    },
    
    localhost: {
      url: "http://127.0.0.1:8545",
      chainId: 1337
    }
  },
  
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts"
  }
};
