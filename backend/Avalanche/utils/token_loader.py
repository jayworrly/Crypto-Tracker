import os
import logging
from web3 import Web3
from functools import lru_cache

class EnhancedTokenLoader:
    def __init__(self, token_directory, w3, erc20_abi=None):
        self.token_directory = token_directory
        self.w3 = w3
        self.erc20_abi = erc20_abi
        self.tokens = {}
        self.load_tokens()

    def load_tokens(self):
        file_path = os.path.join(self.token_directory, 'coins.txt')
        if not os.path.exists(file_path):
            logging.warning(f"Token file not found: {file_path}")
            return

        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split(',')
                        if len(parts) != 3:
                            logging.warning(f"Invalid line in coins.txt: {line}")
                            continue
                        address = Web3.to_checksum_address(parts[0])
                        label = parts[1].strip()
                        decimals = int(parts[2].strip())
                        self.tokens[address.lower()] = {
                            'label': label,
                            'decimals': decimals,
                            'type': 'coin'
                        }
            logging.info(f"Loaded {len(self.tokens)} tokens")
        except Exception as e:
            logging.error(f"Error loading tokens from coins.txt: {str(e)}")

    @lru_cache(maxsize=1000)
    def fetch_token_details(self, address):
        details = {}
        
        if self.erc20_abi:
            try:
                contract = self.w3.eth.contract(address=address, abi=self.erc20_abi)
                for func in ['name', 'symbol', 'decimals']:
                    try:
                        details[func] = getattr(contract.functions, func)().call()
                    except Exception:
                        pass
                if details:
                    details['type'] = 'ERC20'
                    return details
            except Exception:
                pass

        logging.warning(f"Unable to determine token details for {address}")
        return details

    def get_token_info(self, address):
        address = Web3.to_checksum_address(address).lower()
        if address not in self.tokens:
            details = self.fetch_token_details(address)
            if details:
                self.tokens[address] = {
                    'label': details.get('symbol', 'Unknown'),
                    'decimals': details.get('decimals', 18),
                    'type': details.get('type', 'Unknown'),
                    'details': details
                }
            else:
                self.tokens[address] = {
                    'label': 'Unknown',
                    'decimals': 18,
                    'type': 'Unknown',
                    'details': {}
                }
        return self.tokens[address]

    def get_all_tokens(self):
        return self.tokens