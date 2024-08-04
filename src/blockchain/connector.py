# src/blockchain/connector.py

import logging
import time
from web3 import Web3
from web3.middleware import geth_poa_middleware
import yaml
import requests
from blockchain.transactions import analyze_transaction

class BlockchainConnector:
    def __init__(self, config_path):
        self.config = self.load_config(config_path)
        self.w3 = self.connect()
        self.avax_to_usd = self.get_avax_price()

    def load_config(self, config_path):
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)

    def connect(self):
        w3 = Web3(Web3.HTTPProvider(self.config['avalanche']['rpc_url']))
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        if not w3.is_connected():
            raise ConnectionError("Failed to connect to the Avalanche network")
        logging.info("Connected to Avalanche network")
        return w3

    def get_recent_transactions(self, block_count=5):
        """Fetch recent transactions from the latest N blocks."""
        latest_block_number = self.w3.eth.block_number
        transactions = []

        for i in range(block_count):
            block = self.w3.eth.get_block(latest_block_number - i, full_transactions=True)
            transactions.extend(block['transactions'])

        return transactions

    def get_avax_price(self):
        """Fetch the current AVAX price in USD."""
        try:
            response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=avalanche-2&vs_currencies=usd")
            data = response.json()
            return data['avalanche-2']['usd']
        except Exception as e:
            logging.error(f"Error fetching AVAX price: {e}")
            return None

    def get_address_transactions(self, address, start_block=None, end_block=None):
        """Fetch transactions for a specific address over a range of blocks."""
        logging.info(f"Fetching transactions for address {address}")

        if start_block is None:
            start_block = self.w3.eth.block_number - 100  # Example: Start from 100 blocks ago
        if end_block is None:
            end_block = self.w3.eth.block_number  # Default to the latest block

        transactions = []

        for block_number in range(start_block, end_block + 1):
            block = self.w3.eth.get_block(block_number, full_transactions=True)
            for tx in block['transactions']:
                if tx['from'] == address or tx['to'] == address:
                    transactions.append(tx)

        logging.info(f"Found {len(transactions)} transactions for address {address}")
        return transactions
