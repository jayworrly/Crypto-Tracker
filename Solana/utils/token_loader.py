from pathlib import Path
import logging  # Import logging at the top of your file

class TokenLoader:
    def __init__(self, token_file_path="database/solana_tokens.txt"):
        self.token_file_path = Path(token_file_path)
        self.tokens = self.load_tokens()

    def load_tokens(self):
        tokens = {}
        if self.token_file_path.exists():
            with self.token_file_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):  # Skip empty lines or comments
                        continue

                    # Ensure the line has exactly 4 parts
                    parts = line.split(",")
                    if len(parts) != 4:
                        logging.warning(f"Skipping invalid line in {self.token_file_path}: {line}")
                        continue

                    symbol, address, name, decimals = parts
                    tokens[address] = {
                        "symbol": symbol,
                        "address": address,
                        "name": name,
                        "decimals": int(decimals)
                    }
        return tokens



    def get_token_info(self, address):
        return self.tokens.get(address, {"symbol": "Unknown", "name": "Unknown Token", "decimals": 0})

    def get_token_symbol(self, address):
        return self.get_token_info(address)["symbol"]

    def get_token_name(self, address):
        return self.get_token_info(address)["name"]

    def get_token_decimals(self, address):
        return self.get_token_info(address)["decimals"]