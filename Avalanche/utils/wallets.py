# wallets.py

import os
import logging

class WalletLoader:
    def __init__(self, wallet_directory):
        self.wallet_directory = wallet_directory
        self.hot_wallets = {}
        self.whale_wallets = {}
        self.load_wallets()

    def load_wallets(self):
        self.hot_wallets = self._load_wallet_file('cexhotwallet.txt')
        self.whale_wallets = self._load_wallet_file('whales.txt')

    def _load_wallet_file(self, filename):
        wallets = {}
        file_path = os.path.join(self.wallet_directory, filename)
        if not os.path.exists(file_path):
            logging.warning(f"Wallet file not found: {file_path}")
            return wallets

        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        address, label = line.split(',', 1)
                        wallets[address.lower()] = label.strip()
            logging.info(f"Loaded {len(wallets)} wallets from {filename}")
        except Exception as e:
            logging.error(f"Error loading wallets from {filename}: {str(e)}")

        return wallets

    def get_wallet_label(self, address):
        address = address.lower()
        if address in self.hot_wallets:
            return f"Hot Wallet: {self.hot_wallets[address]}"
        elif address in self.whale_wallets:
            return f"Whale Wallet: {self.whale_wallets[address]}"
        return None

    def is_hot_wallet(self, address):
        return address.lower() in self.hot_wallets

    def is_whale_wallet(self, address):
        return address.lower() in self.whale_wallets

    def get_all_hot_wallets(self):
        return self.hot_wallets

    def get_all_whale_wallets(self):
        return self.whale_wallets


# Usage example
# wallet_loader = WalletLoader('/path/to/wallet_directory')
# wallet_label = wallet_loader.get_wallet_label('0x1234...')