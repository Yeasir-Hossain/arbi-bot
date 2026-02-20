const hre = require("hardhat");
const fs = require('fs');
const path = require('path');

/**
 * Deployment script for AI Trading System contracts
 * 
 * Deploys:
 * 1. TestToken A (e.g., "Test USD")
 * 2. TestToken B (e.g., "Test ETH") 
 * 3. SimpleDEX for swapping
 * 
 * Saves addresses to config/contracts.json
 */

async function main() {
  console.log("🚀 Deploying AI Trading System contracts...\n");

  // Get deployer account
  const [deployer] = await hre.ethers.getSigners();
  console.log(`📝 Deploying with account: ${deployer.address}`);

  // Get deployer balance
  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log(`💰 Account balance: ${hre.ethers.formatEther(balance)} ETH\n`);

  // Deploy Token A (simulating USDT)
  console.log("🪙 Deploying Token A (Test USDT)...");
  const TokenA = await hre.ethers.getContractFactory("TestToken");
  const tokenA = await TokenA.deploy(
    "Test USDT",      // name
    "tUSDT",          // symbol
    1000000,          // initial supply (1 million)
    6                 // decimals (like real USDT)
  );
  await tokenA.waitForDeployment();
  const tokenAAddress = await tokenA.getAddress();
  console.log(`✅ Token A deployed to: ${tokenAAddress}\n`);

  // Deploy Token B (simulating ETH)
  console.log("🪙 Deploying Token B (Test ETH)...");
  const TokenB = await hre.ethers.getContractFactory("TestToken");
  const tokenB = await TokenB.deploy(
    "Test ETH",       // name
    "tETH",           // symbol
    100000,           // initial supply (100k)
    18                // decimals (like real ETH)
  );
  await tokenB.waitForDeployment();
  const tokenBAddress = await tokenB.getAddress();
  console.log(`✅ Token B deployed to: ${tokenBAddress}\n`);

  // Deploy DEX
  console.log("🏦 Deploying SimpleDEX...");
  const SimpleDEX = await hre.ethers.getContractFactory("SimpleDEX");
  const dex = await SimpleDEX.deploy(tokenAAddress, tokenBAddress);
  await dex.waitForDeployment();
  const dexAddress = await dex.getAddress();
  console.log(`✅ DEX deployed to: ${dexAddress}\n`);

  // Add initial liquidity
  console.log("💧 Adding initial liquidity...");
  const liquidityA = hre.ethers.parseUnits("100000", 6);  // 100,000 tUSDT
  const liquidityB = hre.ethers.parseUnits("50", 18);     // 50 tETH

  // Approve DEX to spend tokens
  console.log("  Approving DEX to spend Token A...");
  const approveATx = await tokenA.approve(dexAddress, liquidityA);
  await approveATx.wait();

  console.log("  Approving DEX to spend Token B...");
  const approveBTx = await tokenB.approve(dexAddress, liquidityB);
  await approveBTx.wait();

  // Add liquidity
  console.log("  Adding liquidity to DEX...");
  const addLiquidityTx = await dex.addLiquidity(liquidityA, liquidityB);
  await addLiquidityTx.wait();

  console.log(`✅ Liquidity added: ${hre.ethers.formatUnits(liquidityA, 6)} tUSDT + ${hre.ethers.formatUnits(liquidityB, 18)} tETH\n`);

  // Get initial price
  const price = await dex.getPrice();
  console.log(`📊 Initial price: ${hre.ethers.formatEther(price)} tUSDT per tETH\n`);

  // Fund some test accounts
  console.log("💸 Funding test accounts...");
  const accounts = await hre.ethers.getSigners();
  for (let i = 1; i < Math.min(4, accounts.length); i++) {
    const account = accounts[i];
    
    // Send some Token A
    const transferA = await tokenA.transfer(account.address, hre.ethers.parseUnits("10000", 6));
    await transferA.wait();
    
    // Send some Token B
    const transferB = await tokenB.transfer(account.address, hre.ethers.parseUnits("5", 18));
    await transferB.wait();
    
    console.log(`  Funded account ${i}: ${account.address}`);
  }
  console.log("");

  // Save deployment info
  const deploymentInfo = {
    tokenA: tokenAAddress,
    tokenB: tokenBAddress,
    dex: dexAddress,
    network: "localhost",
    chainId: 1337,
    deployedAt: new Date().toISOString(),
    deployer: deployer.address,
    initialPrice: hre.ethers.formatEther(price)
  };

  // Save to config file
  const configPath = path.join(__dirname, '..', 'config', 'contracts.json');
  fs.writeFileSync(configPath, JSON.stringify(deploymentInfo, null, 2));
  console.log(`📁 Deployment info saved to: ${configPath}\n`);

  // Summary
  console.log("═══════════════════════════════════════════════════════");
  console.log("📋 DEPLOYMENT SUMMARY");
  console.log("═══════════════════════════════════════════════════════");
  console.log(`Token A (tUSDT):  ${tokenAAddress}`);
  console.log(`Token B (tETH):   ${tokenBAddress}`);
  console.log(`DEX Contract:     ${dexAddress}`);
  console.log(`Initial Price:    ${hre.ethers.formatEther(price)} tUSDT/tETH`);
  console.log("═══════════════════════════════════════════════════════");
  console.log("\n✅ Deployment complete!");
  console.log("\nNext steps:");
  console.log("1. Start the Python Web3 client");
  console.log("2. Run AI trading agent");
  console.log("3. Monitor trades on the local DEX");
}

// Handle deployment
main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Deployment failed:", error);
    process.exit(1);
  });
