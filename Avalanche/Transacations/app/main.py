# app/main.py

import argparse
import logging
import time
from decimal import Decimal
from web3 import Web3
from blockchain.connector import BlockchainConnector
from analysis import TransactionAnalyzer
from utils.helpers import setup_logging
import os

AVALANCHE_ECO_DIR = 'app/avalanche_eco'

def parse_arguments():
    parser = argparse.ArgumentParser(description="AvaxWhale Transaction Tracker")
    config_path = os.path.abspath('config/config.yaml')
    print(f"Resolved config path: {config_path}")  # Debugging line
    parser.add_argument("--config", default=config_path, help="Path to configuration file")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set the logging level")
    parser.add_argument("--interval", type=int, default=60, help="Interval in seconds between checks")
    return parser.parse_args()

def classify_transaction(tx, address_categories):
    """Classify a transaction based on address categories."""
    for category, addresses in address_categories.items():
        if tx['to'].lower() in addresses:
            return f"{category}: {addresses[tx['to'].lower()]}"
        if tx['from'].lower() in addresses:
            return f"{category}: {addresses[tx['from'].lower()]} (sender)"
    logging.debug(f"Unknown address: to={tx['to']}, from={tx['from']}")
    return 'unknown'

def load_addresses_from_files(directory):
    """Load addresses and labels from text files in a given directory."""
    address_categories = {}
    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            category = filename.replace(".txt", "")
            address_categories[category] = {}

            filepath = os.path.join(directory, filename)
            with open(filepath, 'r') as file:
                for line in file:
                    line = line.strip()
                    if line:
                        try:
                            address, label = line.split(',', 1)
                            address_categories[category][address.strip().lower()] = label.strip()
                        except ValueError as e:
                            logging.error(f"Error parsing line '{line}' in {filename}: {e}")
    return address_categories

def track_transactions(args):
    setup_logging(args.log_level)

    logging.info("Starting AvaxWhale Transaction Tracker")

    try:
        # Initialize blockchain connector and transaction analyzer
        connector = BlockchainConnector(args.config)
        analyzer = TransactionAnalyzer(connector)

        # Define a large transaction threshold (in USD)
        large_transaction_threshold = 10000  # Set your threshold here, e.g., $10,000

        # Load addresses from the files in the avalanche_eco directory
        address_categories = load_addresses_from_files(AVALANCHE_ECO_DIR)

        # Log the number of addresses loaded for each category
        for category, addresses in address_categories.items():
            logging.debug(f"Loaded {len(addresses)} addresses for category {category}")

        while True:
            try:
                # Fetch recent transactions
                transactions = connector.get_recent_transactions()
                logging.debug(f"Fetched {len(transactions)} transactions")

                # Filter for large transactions
                large_transactions = [
                    tx for tx in transactions
                    if float(Web3.from_wei(tx['value'], 'ether')) * float(connector.avax_to_usd) >= large_transaction_threshold
                ]
                logging.debug(f"Found {len(large_transactions)} large transactions")

                # Analyze large transactions
                if large_transactions:
                    logging.info(f"Found {len(large_transactions)} large transactions")
                    for tx in large_transactions:
                        tx_value_avax = Web3.from_wei(tx['value'], 'ether')
                        tx_value_usd = float(tx_value_avax) * float(connector.avax_to_usd)

                        # Classify transaction
                        tx_type = classify_transaction(tx, address_categories)
                        logging.info(f"Large transaction detected: Hash={tx['hash'].hex()}, Value={tx_value_avax:.2f} AVAX, "
                                     f"Value in USD={tx_value_usd:.2f}, From={tx['from']}, To={tx['to']}, Type={tx_type}")
                else:
                    logging.debug("No large transactions found in this batch")

                # Sleep for the specified interval
                time.sleep(args.interval)

            except Exception as e:
                logging.error(f"Error during monitoring: {e}")
                time.sleep(5)

    except Exception as e:
        logging.error(f"An error occurred during initialization: {str(e)}")
    
    logging.info("AvaxWhale Transaction Tracker finished")

if __name__ == "__main__":
    args = parse_arguments()
    track_transactions(args)
