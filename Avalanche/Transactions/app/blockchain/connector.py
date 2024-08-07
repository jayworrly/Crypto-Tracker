# connector.py

import logging
import os
import json
import time
from web3 import Web3
from web3.exceptions import ContractLogicError
from web3.middleware import geth_poa_middleware
import yaml
import requests

class BlockchainConnector:
    def __init__(self, config_path, abi_directory='router_abis'):
        self.config = self.load_config(config_path)
        self.w3 = self.connect()
        self.avax_to_usd = self.get_avax_price()
        self.abis = self.load_abis(abi_directory)  # Load ABIs

    def load_config(self, config_path):
        """Load the configuration file for blockchain connection."""
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
                logging.info(f"Configuration loaded from {config_path}")
                return config
        except FileNotFoundError as e:
            logging.error(f"Config file not found: {e}")
            raise
        except yaml.YAMLError as e:
            logging.error(f"Error parsing config file: {e}")
            raise

    def connect(self):
        """Establish connection to the Avalanche blockchain network."""
        try:
            w3 = Web3(Web3.HTTPProvider(self.config['avalanche']['rpc_url']))
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            if not w3.is_connected():
                raise ConnectionError("Failed to connect to the Avalanche network")
            logging.info("Connected to Avalanche network")
            return w3
        except Exception as e:
            logging.error(f"Error connecting to Avalanche network: {e}")
            raise

    def load_abis(self, directory):
        """Load ABIs from the specified directory."""
        abis = {}
        try:
            for filename in os.listdir(directory):
                if filename.endswith('.json'):
                    filepath = os.path.join(directory, filename)
                    with open(filepath, 'r') as file:
                        abis[filename] = json.load(file)
                        logging.info(f"Loaded ABI from {filename}")
        except Exception as e:
            logging.error(f"Error loading ABIs: {e}")
        return abis

    def get_recent_transactions(self, block_count=5):
        """Fetch recent transactions from the latest N blocks."""
        try:
            latest_block_number = self.w3.eth.block_number
            transactions = []

            for i in range(block_count):
                block = self.w3.eth.get_block(latest_block_number - i, full_transactions=True)
                transactions.extend(block['transactions'])

            logging.info(f"Retrieved {len(transactions)} transactions from the last {block_count} blocks")
            return transactions
        except Exception as e:
            logging.error(f"Error retrieving recent transactions: {e}")
            return []

    def get_avax_price(self):
        """Fetch the current AVAX price in USD."""
        try:
            response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=avalanche-2&vs_currencies=usd")
            response.raise_for_status()
            data = response.json()
            avax_price = data['avalanche-2']['usd']
            logging.info(f"Current AVAX price: ${avax_price:.2f} USD")
            return avax_price
        except requests.RequestException as e:
            logging.error(f"Error fetching AVAX price: {e}")
            return None

    def get_token_info(self, token_address):
        """Fetch token information from the Avalanche C-Chain without relying on external APIs."""
        try:
            # ERC20 ABI for name, symbol, decimals, and totalSupply
            abi = [
                {"constant":True,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"type":"function"},
                {"constant":True,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"},
                {"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},
                {"constant":True,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"type":"function"}
            ]
            
            contract = self.w3.eth.contract(address=token_address, abi=abi)
            
            token_info = {
                "address": token_address,
                "name": None,
                "symbol": None,
                "decimals": None,
                "total_supply": None
            }

            # Attempt to call each function, handling potential errors
            try:
                token_info["name"] = contract.functions.name().call()
            except ContractLogicError:
                logging.warning(f"Could not fetch name for token {token_address}")

            try:
                token_info["symbol"] = contract.functions.symbol().call()
            except ContractLogicError:
                logging.warning(f"Could not fetch symbol for token {token_address}")

            try:
                token_info["decimals"] = contract.functions.decimals().call()
            except ContractLogicError:
                logging.warning(f"Could not fetch decimals for token {token_address}")

            try:
                total_supply = contract.functions.totalSupply().call()
                token_info["total_supply"] = self.w3.from_wei(total_supply, 'ether')
            except ContractLogicError:
                logging.warning(f"Could not fetch total supply for token {token_address}")

            # Check if we were able to fetch any information
            if all(value is None for value in token_info.values()):
                logging.error(f"Could not fetch any information for token {token_address}")
                return None

            return token_info

        except Exception as e:
            logging.error(f"Error fetching token info for {token_address}: {str(e)}")
            return None

    def get_token_balance(self, token_address, wallet_address):
        """Fetch the balance of a specific token for a given wallet address."""
        try:
            # ERC20 ABI for balanceOf function
            abi = [
                {"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},
                {"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}
            ]
            
            contract = self.w3.eth.contract(address=token_address, abi=abi)
            
            balance_wei = contract.functions.balanceOf(wallet_address).call()
            decimals = contract.functions.decimals().call()
            
            balance = balance_wei / (10 ** decimals)
            
            return balance
        except Exception as e:
            logging.error(f"Error fetching token balance for {token_address} and wallet {wallet_address}: {str(e)}")
            return None

    def get_address_transactions(self, address, time_period):
        """
        Fetch transactions for a given address over a specified time period.
        
        Args:
            address (str): The address to fetch transactions for.
            time_period (str): Time period for fetching transactions (e.g., "24h", "7d", "30d").
        
        Returns:
            list: List of transactions for the given address.
        """
        try:
            # Convert time_period to number of blocks
            # This is a simplified approach; you might want to implement a more accurate conversion
            blocks_per_day = 24 * 60 * 60 / 2  # Assuming 2-second block time
            days = self._convert_time_period_to_days(time_period)
            blocks = int(blocks_per_day * days)

            latest_block = self.w3.eth.get_block('latest')
            from_block = latest_block.number - blocks
            to_block = 'latest'

            # Fetch transactions
            transactions = []
            for i in range(from_block, latest_block.number + 1):
                block = self.w3.eth.get_block(i, full_transactions=True)
                for tx in block.transactions:
                    if tx['from'].lower() == address.lower() or tx['to'] and tx['to'].lower() == address.lower():
                        transactions.append(tx)

            logging.info(f"Retrieved {len(transactions)} transactions for address {address} over {time_period}")
            return transactions
        except Exception as e:
            logging.error(f"Error fetching transactions for address {address}: {str(e)}")
            return []

    def _convert_time_period_to_days(self, time_period):
        """Convert a time period string to number of days."""
        units = {'h': 1/24, 'd': 1, 'w': 7}
        try:
            value = float(time_period[:-1])
            unit = time_period[-1].lower()
            if unit not in units:
                raise ValueError(f"Unsupported time unit: {unit}")
            return value * units[unit]
        except (ValueError, IndexError):
            raise ValueError(f"Invalid time period format: {time_period}")

