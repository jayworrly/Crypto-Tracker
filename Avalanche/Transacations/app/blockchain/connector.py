# connector.py

import logging
import time
from web3 import Web3
from web3.middleware import geth_poa_middleware
import yaml
import requests
from blockchain.transactions import analyze_transaction  # Use full import path

class BlockchainConnector:
    def __init__(self, config_path):
        self.config = self.load_config(config_path)
        self.w3 = self.connect()
        self.avax_to_usd = self.get_avax_price()

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
