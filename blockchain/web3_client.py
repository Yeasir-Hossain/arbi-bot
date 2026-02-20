"""
Web3 Client for AI Trading System
Python interface to interact with local Hardhat blockchain and smart contracts
"""

from web3 import Web3
from web3.middleware import geth_poa_middleware
import json
from pathlib import Path
from loguru import logger
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass
import os


@dataclass
class ContractInfo:
    """Contract address and ABI"""
    address: str
    abi: list
    contract: Any  # web3.contract.Contract


class BlockchainClient:
    """
    Client for interacting with the local blockchain
    
    Features:
    - Connect to Hardhat local node
    - Load and interact with deployed contracts
    - Execute token swaps
    - Query balances and prices
    """

    def __init__(self, rpc_url: str = "http://localhost:8545"):
        """
        Initialize blockchain client
        
        Args:
            rpc_url: RPC endpoint URL for the blockchain node
        """
        self.rpc_url = rpc_url
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Inject POA middleware for local dev chains
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        # Load contract information
        self.contracts: Dict[str, ContractInfo] = {}
        self._load_contracts()
        
        if self.w3.is_connected():
            logger.info(f"Connected to blockchain: {rpc_url}")
            chain_id = self.w3.eth.chain_id
            logger.info(f"Chain ID: {chain_id}")
            
            # Get latest block
            latest_block = self.w3.eth.block_number
            logger.info(f"Latest block: {latest_block}")
        else:
            logger.error(f"Failed to connect to blockchain: {rpc_url}")
            raise ConnectionError(
                f"Cannot connect to blockchain at {rpc_url}. "
                "Make sure Hardhat node is running: `npx hardhat node`"
            )

    def _load_contracts(self) -> None:
        """Load contract addresses and ABIs from config and artifacts"""
        config_path = Path(__file__).parent.parent / "config" / "contracts.json"
        
        if not config_path.exists():
            logger.warning("contracts.json not found - contracts may not be deployed")
            return
        
        with open(config_path) as f:
            addresses = json.load(f)
        
        artifacts_path = Path(__file__).parent / "artifacts" / "contracts"
        
        if not artifacts_path.exists():
            logger.warning("Artifacts not found - run `npx hardhat compile`")
            return
        
        # Load Token A
        try:
            token_a_artifact = self._load_artifact("TestToken")
            self.contracts['tokenA'] = ContractInfo(
                address=addresses['tokenA'],
                abi=token_a_artifact['abi'],
                contract=self.w3.eth.contract(
                    address=addresses['tokenA'],
                    abi=token_a_artifact['abi']
                )
            )
            logger.info(f"Loaded Token A: {addresses['tokenA']}")
        except Exception as e:
            logger.warning(f"Failed to load Token A: {e}")
        
        # Load Token B
        try:
            token_b_artifact = self._load_artifact("TestToken")
            self.contracts['tokenB'] = ContractInfo(
                address=addresses['tokenB'],
                abi=token_b_artifact['abi'],
                contract=self.w3.eth.contract(
                    address=addresses['tokenB'],
                    abi=token_b_artifact['abi']
                )
            )
            logger.info(f"Loaded Token B: {addresses['tokenB']}")
        except Exception as e:
            logger.warning(f"Failed to load Token B: {e}")
        
        # Load DEX
        try:
            dex_artifact = self._load_artifact("SimpleDEX")
            self.contracts['dex'] = ContractInfo(
                address=addresses['dex'],
                abi=dex_artifact['abi'],
                contract=self.w3.eth.contract(
                    address=addresses['dex'],
                    abi=dex_artifact['abi']
                )
            )
            logger.info(f"Loaded DEX: {addresses['dex']}")
        except Exception as e:
            logger.warning(f"Failed to load DEX: {e}")

    def _load_artifact(self, contract_name: str) -> dict:
        """Load contract artifact (ABI) from Hardhat output"""
        artifact_path = Path(__file__).parent / "artifacts" / "contracts" / f"{contract_name}.sol" / f"{contract_name}.json"
        
        with open(artifact_path) as f:
            return json.load(f)

    def get_balance(self, token: str, address: str) -> float:
        """
        Get token balance for an address
        
        Args:
            token: Token key ('tokenA', 'tokenB', or 'eth')
            address: Wallet address
            
        Returns:
            Balance as float (normalized by decimals)
        """
        if token == 'eth':
            balance = self.w3.eth.get_balance(address)
            return self.w3.from_wei(balance, 'ether')
        
        if token not in self.contracts:
            raise ValueError(f"Unknown token: {token}")
        
        contract = self.contracts[token].contract
        balance = contract.functions.balanceOf(address).call()
        decimals = contract.functions.decimals().call()
        
        return balance / (10 ** decimals)

    def get_eth_balance(self, address: str) -> float:
        """Get ETH balance for an address"""
        return self.get_balance('eth', address)

    def get_price(self) -> float:
        """
        Get current DEX price (Token A per Token B)
        
        Returns:
            Price as float
        """
        if 'dex' not in self.contracts:
            raise ValueError("DEX contract not loaded")
        
        dex = self.contracts['dex'].contract
        price = dex.functions.getPrice().call()
        return price / 1e18

    def get_reserves(self) -> Tuple[float, float]:
        """
        Get DEX liquidity reserves
        
        Returns:
            Tuple of (reserveA, reserveB)
        """
        if 'dex' not in self.contracts:
            raise ValueError("DEX contract not loaded")
        
        dex = self.contracts['dex'].contract
        reserves = dex.functions.getReserves().call()
        
        # Get token decimals
        token_a_decimals = self.contracts['tokenA'].contract.functions.decimals().call()
        token_b_decimals = self.contracts['tokenB'].contract.functions.decimals().call()
        
        reserve_a = reserves[0] / (10 ** token_a_decimals)
        reserve_b = reserves[1] / (10 ** token_b_decimals)
        
        return reserve_a, reserve_b

    def get_account(self, index: int = 0) -> Tuple[str, str]:
        """
        Get account address and private key from Hardhat's default accounts
        
        Args:
            index: Account index (0-9)
            
        Returns:
            Tuple of (address, private_key)
        """
        # Hardhat's default mnemonic
        mnemonic = "test test test test test test test test test test test junk"
        
        self.w3.eth.account.enable_unaudited_hdwallet_features()
        account = self.w3.eth.account.from_mnemonic(
            mnemonic,
            account_path=f"m/44'/60'/0'/0/{index}"
        )
        
        return account.address, account.key.hex()

    def get_account_from_key(self, private_key: str) -> str:
        """
        Get address from private key
        
        Args:
            private_key: Private key (hex string)
            
        Returns:
            Wallet address
        """
        account = self.w3.eth.account.from_key(private_key)
        return account.address

    def swap_tokens(
        self,
        from_token: str,
        amount: float,
        account_address: str,
        private_key: str,
        slippage: float = 0.01
    ) -> str:
        """
        Execute token swap on DEX
        
        Args:
            from_token: Token to swap from ('tokenA' or 'tokenB')
            amount: Amount to swap
            account_address: Sender's address
            private_key: Sender's private key
            slippage: Allowed slippage (default 1%)
            
        Returns:
            Transaction hash
        """
        if 'dex' not in self.contracts:
            raise ValueError("DEX contract not loaded")
        
        if from_token not in ['tokenA', 'tokenB']:
            raise ValueError(f"Invalid token: {from_token}")
        
        dex = self.contracts['dex'].contract
        token_contract = self.contracts[from_token].contract
        
        # Convert amount to wei
        decimals = token_contract.functions.decimals().call()
        amount_wei = int(amount * (10 ** decimals))
        
        # Get nonce
        nonce = self.w3.eth.get_transaction_count(account_address)
        gas_price = self.w3.eth.gas_price
        
        # Step 1: Approve DEX to spend tokens
        logger.info(f"Approving DEX to spend {amount} {from_token}...")
        
        approve_tx = token_contract.functions.approve(
            dex.address,
            amount_wei
        ).build_transaction({
            'from': account_address,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': gas_price,
            'chainId': self.w3.eth.chain_id
        })
        
        signed_approve = self.w3.eth.account.sign_transaction(approve_tx, private_key)
        approve_hash = self.w3.eth.send_raw_transaction(signed_approve.rawTransaction)
        approve_receipt = self.w3.eth.wait_for_transaction_receipt(approve_hash)
        
        if approve_receipt['status'] != 1:
            raise Exception("Token approval failed")
        
        logger.info(f"✅ Approval successful: {approve_hash.hex()}")
        
        # Step 2: Execute swap
        logger.info(f"Executing swap: {amount} {from_token}...")
        
        if from_token == 'tokenA':
            swap_func = dex.functions.swapAforB(amount_wei)
            to_token = 'tokenB'
        else:
            swap_func = dex.functions.swapBforA(amount_wei)
            to_token = 'tokenA'
        
        # Estimate gas
        try:
            gas_estimate = swap_func.estimate_gas({'from': account_address})
        except Exception as e:
            logger.warning(f"Gas estimate failed: {e}, using default")
            gas_estimate = 200000
        
        swap_tx = swap_func.build_transaction({
            'from': account_address,
            'nonce': nonce + 1,
            'gas': gas_estimate,
            'gasPrice': gas_price,
            'chainId': self.w3.eth.chain_id
        })
        
        signed_swap = self.w3.eth.account.sign_transaction(swap_tx, private_key)
        swap_hash = self.w3.eth.send_raw_transaction(signed_swap.rawTransaction)
        
        logger.info(f"Swap transaction sent: {swap_hash.hex()}")
        
        # Wait for receipt
        receipt = self.w3.eth.wait_for_transaction_receipt(swap_hash)
        
        if receipt['status'] != 1:
            raise Exception("Swap transaction failed")
        
        # Calculate received amount from logs
        amount_out = self._parse_swap_logs(receipt, from_token)
        
        logger.info(f"✅ Swap successful!")
        logger.info(f"   Swapped: {amount} {from_token}")
        logger.info(f"   Received: {amount_out} {to_token}")
        logger.info(f"   TX Hash: {swap_hash.hex()}")
        
        return swap_hash.hex()

    def _parse_swap_logs(self, receipt: dict, from_token: str) -> float:
        """Parse swap amount from transaction logs"""
        dex = self.contracts['dex'].contract
        
        # Get Swap event
        swap_event = dex.events.Swap()
        
        # Parse logs
        for log in receipt['logs']:
            try:
                event_data = swap_event.process_log(log)
                if event_data['args']['isAtoB'] == (from_token == 'tokenA'):
                    amount_out = event_data['args']['amountOut']
                    
                    # Get output token decimals
                    to_token = 'tokenB' if from_token == 'tokenA' else 'tokenA'
                    decimals = self.contracts[to_token].contract.functions.decimals().call()
                    
                    return amount_out / (10 ** decimals)
            except Exception:
                continue
        
        return 0.0

    def get_transaction_status(self, tx_hash: str) -> dict:
        """
        Get transaction status
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Transaction info dict
        """
        tx = self.w3.eth.get_transaction(tx_hash)
        receipt = self.w3.eth.get_transaction_receipt(tx_hash)
        
        return {
            'hash': tx_hash,
            'from': tx['from'],
            'to': tx['to'],
            'value': self.w3.from_wei(tx.get('value', 0), 'ether'),
            'gas_used': receipt['gasUsed'],
            'status': 'success' if receipt['status'] == 1 else 'failed',
            'block_number': receipt['blockNumber'],
            'confirmations': self.w3.eth.block_number - receipt['blockNumber'] + 1
        }


# Example usage
if __name__ == "__main__":
    from config import setup_logging
    setup_logging()
    
    try:
        client = BlockchainClient()
        
        # Get first account
        address, private_key = client.get_account(0)
        
        print(f"\n{'='*50}")
        print(f"Account: {address}")
        print(f"{'='*50}")
        
        # Check balances
        eth_balance = client.get_eth_balance(address)
        tokenA_balance = client.get_balance('tokenA', address)
        tokenB_balance = client.get_balance('tokenB', address)
        
        print(f"ETH Balance:     {eth_balance:.4f}")
        print(f"Token A Balance: {tokenA_balance:.2f}")
        print(f"Token B Balance: {tokenB_balance:.2f}")
        
        # Get price
        price = client.get_price()
        print(f"\nCurrent Price:   {price:.4f} TokenA/TokenB")
        
        # Get reserves
        reserve_a, reserve_b = client.get_reserves()
        print(f"Liquidity:       {reserve_a:.2f} TokenA + {reserve_b:.2f} TokenB")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        print("\nMake sure Hardhat node is running:")
        print("  cd blockchain && npx hardhat node")
