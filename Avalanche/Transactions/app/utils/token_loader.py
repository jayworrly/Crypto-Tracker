import os
import logging
from web3 import Web3
import json
import requests

class EnhancedTokenLoader:
    def __init__(self, token_directory, w3, erc20_abi=None, erc721_abi=None, erc1155_abi=None):
        self.token_directory = token_directory
        self.w3 = w3
        self.erc20_abi = erc20_abi
        self.erc721_abi = erc721_abi
        self.erc1155_abi = erc1155_abi
        self.tokens = {}
        self.load_tokens()

    def load_tokens(self):
        token_files = ['coins.txt', 'token_mapping.txt']
        for token_file in token_files:
            file_path = os.path.join(self.token_directory, token_file)
            if not os.path.exists(file_path):
                logging.warning(f"Token file not found: {file_path}")
                continue

            try:
                with open(file_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            parts = line.split(',')
                            address = parts[0].lower()
                            label = parts[1].strip()
                            pair_id = parts[2].strip() if len(parts) > 2 else None
                            self.tokens[address] = {
                                'label': label,
                                'type': 'coin' if token_file == 'coins.txt' else 'token',
                                'details': self.fetch_token_details(address),
                                'pair_id': pair_id
                            }
            except Exception as e:
                logging.error(f"Error loading tokens from {token_file}: {str(e)}")

        logging.info(f"Loaded {len(self.tokens)} tokens")

    def fetch_token_details(self, address):
        details = {}
        
        # Select the correct ABI
        contract_abi = self.erc20_abi if self.erc20_abi else []

        contract = self.w3.eth.contract(address=address, abi=contract_abi)

        for func in ['name', 'symbol', 'decimals']:
            try:
                details[func] = getattr(contract.functions, func)().call()
            except Exception as e:
                logging.error(f"Error fetching {func} for token {address}: {str(e)}")

        return details

    def get_token_info(self, address):
        return self.tokens.get(address.lower())

    def update_token_price(self, address, price):
        address = address.lower()
        if address in self.tokens:
            self.tokens[address]['price'] = price
            logging.info(f"Updated price for {self.tokens[address]['label']} ({address}): {price}")
        else:
            logging.warning(f"Attempted to update price for unknown token: {address}")

    def get_token_price(self, address):
        token_info = self.get_token_info(address)
        if token_info and token_info.get('pair_id'):
            return self.fetch_dexscreener_data(token_info['pair_id'])
        logging.warning(f"No pair ID available for token {address}")
        return None

    def fetch_dexscreener_data(self, pair_id, max_retries=3):
        url = f"https://api.dexscreener.com/latest/dex/pairs/avalanche/{pair_id}"
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                if 'pair' in data and 'priceUsd' in data['pair']:
                    return float(data['pair']['priceUsd'])
                else:
                    logging.warning(f"Invalid response structure for pair {pair_id}: {data}")
                    return None
            except requests.RequestException as e:
                logging.warning(f"Request failed for pair {pair_id} (Attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)
        logging.error(f"Failed to fetch data for pair {pair_id} after {max_retries} attempts")
        return None

    def get_all_tokens(self):
        return self.tokens
