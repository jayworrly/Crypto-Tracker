import os
import json
import logging
from web3 import Web3
from web3.exceptions import ContractLogicError

class EnhancedTokenLoader:
    def __init__(self, token_directory, w3):
        self.token_directory = token_directory
        self.w3 = w3
        self.tokens = {}
        self.load_tokens()

    def load_tokens(self):
        token_files = ['coins.txt']  # Add more files here if needed
        for token_file in token_files:
            file_path = os.path.join(self.token_directory, token_file)
            if not os.path.exists(file_path):
                logging.warning(f"Token file not found: {file_path}")
                continue
            
            try:
                with open(file_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):  # Ignore empty lines and comments
                            try:
                                address, label = line.split(',', 1)
                                address = address.lower()  # Normalize addresses to lowercase
                                self.tokens[address] = {
                                    'label': label.strip(),
                                    'type': token_file[:-4],  # Remove .txt
                                    'details': self.fetch_token_details(address)
                                }
                            except ValueError:
                                logging.warning(f"Invalid line in {token_file}: {line}")
            except Exception as e:
                logging.error(f"Error loading tokens from {token_file}: {str(e)}")

        logging.info(f"Loaded {len(self.tokens)} tokens")

    def fetch_token_details(self, address):
        erc20_abi = json.loads('[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}]')
        
        details = {}
        contract = self.w3.eth.contract(address=address, abi=erc20_abi)

        for func in ['name', 'symbol', 'decimals']:
            try:
                details[func] = getattr(contract.functions, func)().call()
            except ContractLogicError:
                logging.warning(f"Could not fetch {func} for token {address}")
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

    def get_all_tokens(self):
        return self.tokens

# Usage example (commented out to avoid execution)
w3 = Web3(Web3.HTTPProvider('https://api.avax.network/ext/bc/C/rpc'))
token_loader = EnhancedTokenLoader('/transactions/app/avalanche_eco', w3)
# token_info = token_loader.get_token_info('0x1234...')
