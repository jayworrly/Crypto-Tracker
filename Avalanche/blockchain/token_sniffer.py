import logging
from web3 import Web3
from web3.exceptions import ContractLogicError
import json
import time
import sqlite3
import os
import threading

class TokenSniffer:
    def __init__(self, w3, database_dir):
        self.w3 = w3
        self.database_dir = database_dir
        self.db_path = os.path.join(database_dir, 'tokens.db')
        self.coins_file = os.path.join(database_dir, 'coins.txt')
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.setup_database()
        self.load_abis()

    def setup_database(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tokens (
                address TEXT PRIMARY KEY,
                name TEXT,
                symbol TEXT,
                token_type TEXT,
                discovered_at INTEGER
            )
        ''')
        self.conn.commit()

    def load_abis(self):
        # Adjust these paths as needed
        erc_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'erc')
        with open(os.path.join(erc_dir, 'erc20_abi.json'), 'r') as f:
            self.ERC20_ABI = json.load(f)
        with open(os.path.join(erc_dir, 'erc721_abi.json'), 'r') as f:
            self.ERC721_ABI = json.load(f)
        with open(os.path.join(erc_dir, 'erc1155_abi.json'), 'r') as f:
            self.ERC1155_ABI = json.load(f)

    def is_token_contract(self, address):
        for abi in [self.ERC20_ABI, self.ERC721_ABI, self.ERC1155_ABI]:
            contract = self.w3.eth.contract(address=address, abi=abi)
            try:
                contract.functions.name().call()
                contract.functions.symbol().call()
                return True
            except ContractLogicError:
                continue
        return False

    def get_token_info(self, address):
        for abi in [self.ERC20_ABI, self.ERC721_ABI, self.ERC1155_ABI]:
            contract = self.w3.eth.contract(address=address, abi=abi)
            try:
                name = contract.functions.name().call()
                symbol = contract.functions.symbol().call()
                token_type = "ERC20" if abi == self.ERC20_ABI else "ERC721" if abi == self.ERC721_ABI else "ERC1155"
                return name, symbol, token_type
            except ContractLogicError:
                continue
        return None, None, None

    def store_token(self, address, name, symbol, token_type):
        self.cursor.execute('''
            INSERT OR REPLACE INTO tokens (address, name, symbol, token_type, discovered_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (address, name, symbol, token_type, int(time.time())))
        self.conn.commit()
        self.update_coins_file(address, symbol)

    def update_coins_file(self, address, symbol):
        if os.path.exists(self.coins_file):
            with open(self.coins_file, 'r') as f:
                existing_tokens = f.read().splitlines()
        else:
            existing_tokens = []

        new_entry = f"{address},{symbol}"
        if new_entry not in existing_tokens:
            with open(self.coins_file, 'a') as f:
                f.write(f"{new_entry}\n")
            logging.info(f"Added new token to coins.txt: {symbol} ({address})")

    def scan_blocks_for_tokens(self, start_block, end_block):
        for block_number in range(start_block, end_block + 1):
            block = self.w3.eth.get_block(block_number, full_transactions=True)
            for tx in block.transactions:
                if tx['to'] is None:  # Contract creation transaction
                    receipt = self.w3.eth.get_transaction_receipt(tx['hash'])
                    contract_address = receipt['contractAddress']
                    if contract_address and self.is_token_contract(contract_address):
                        name, symbol, token_type = self.get_token_info(contract_address)
                        if name and symbol:
                            logging.info(f"New token found: {name} ({symbol}) at {contract_address}")
                            self.store_token(contract_address, name, symbol, token_type)

    def run(self):
        latest_block = self.w3.eth.block_number
        while True:
            try:
                current_block = self.w3.eth.block_number
                if current_block > latest_block:
                    self.scan_blocks_for_tokens(latest_block + 1, current_block)
                    latest_block = current_block
                time.sleep(10)  # Wait 10 seconds before checking for new blocks
            except Exception as e:
                logging.error(f"An error occurred in token sniffer: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying

    def start(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread