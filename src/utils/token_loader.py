import os
import logging

# Define the path relative to the project root
TOKEN_DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), '../avalanche_eco'))

def load_token_addresses():
    token_files = ['defi.txt', 'meme.txt', 'stablecoins.txt']
    token_labels = {}

    for token_file in token_files:
        try:
            with open(os.path.join(TOKEN_DIRECTORY, token_file), 'r') as f:
                for line in f:
                    address, label = line.strip().split(',')
                    token_labels[address] = label
        except FileNotFoundError as e:
            logging.error(f"Error loading token addresses: {e}")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")

    return token_labels
