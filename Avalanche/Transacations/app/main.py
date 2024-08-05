# app/main.py

import argparse
import logging
import time
from decimal import Decimal
import sqlite3
from web3 import Web3
from blockchain.connector import BlockchainConnector
from analysis import TransactionAnalyzer
from utils.helpers import setup_logging

# Path to the SQLite database
DATABASE = 'app/database/avalanche_addresses.db'

def connect_db():
    """Establish a connection to the SQLite database."""
    return sqlite3.connect(DATABASE)

def load_addresses_from_db():
    """Load addresses and labels from the database."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT address, label, category FROM addresses")
    addresses = cursor.fetchall()
    conn.close()

    # Organize addresses by category
    address_categories = {}
    for address, label, category in addresses:
        if category not in address_categories:
            address_categories[category] = {}
        address_categories[category][address.lower()] = label
    return address_categories

def classify_transaction(tx, address_categories):
    """Classify a transaction based on address categories."""
    for category, addresses in address_categories.items():
        if tx['to'].lower() in addresses:
            return f"{category}: {addresses[tx['to'].lower()]}"
        if tx['from'].lower() in addresses:
            return f"{category}: {addresses[tx['from'].lower()]} (sender)"
    logging.debug(f"Unknown address: to={tx['to']}, from={tx['from']}")
    return 'unknown'

def parse_arguments():
    parser = argparse.ArgumentParser(description="AvaxWhale Transaction Tracker")
    parser.add_argument("--config", default="../config/config.yaml", help="Path to configuration file")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set the logging level")
    parser.add_argument("--interval", type=int, default=60, help="Interval in seconds between checks")
    return parser.parse_args()

def track_transactions(args):
    setup_logging(args.log_level)

    logging.info("Starting AvaxWhale Transaction Tracker")

    try:
        # Initialize blockchain connector and transaction analyzer
        connector = BlockchainConnector(args.config)
        analyzer = TransactionAnalyzer(connector)

        # Define a large transaction threshold (in USD)
        large_transaction_threshold = 10000  # Set your threshold here, e.g., $10,000

        # Load addresses from the database
        address_categories = load_addresses_from_db()

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
