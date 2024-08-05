import argparse
import logging
import time
from decimal import Decimal
from web3 import Web3
from blockchain.connector import BlockchainConnector
from analysis import TransactionAnalyzer
from utils.helpers import setup_logging

def parse_arguments():
    parser = argparse.ArgumentParser(description="AvaxWhale Transaction Tracker")
    parser.add_argument("--config", default="../config/config.yaml", help="Path to configuration file")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set the logging level")
    parser.add_argument("--interval", type=int, default=60, help="Interval in seconds between checks")
    return parser.parse_args()

def read_addresses_from_file(file_path):
    """Read addresses and labels from a text file."""
    addresses = {}
    with open(file_path, 'r') as file:
        for line in file.readlines():
            if line.strip():
                address, label = line.strip().split(',', 1)
                addresses[address.strip().lower()] = label.strip()
    return addresses

def classify_transaction(tx, address_categories):
    """Classify a transaction based on address categories."""
    for category, addresses in address_categories.items():
        if tx['to'].lower() in addresses:
            return f"{category}: {addresses[tx['to'].lower()]}"
        if tx['from'].lower() in addresses:
            return f"{category}: {addresses[tx['from'].lower()]} (sender)"
    logging.debug(f"Unknown address: to={tx['to']}, from={tx['from']}")
    return 'unknown'

def main():
    args = parse_arguments()
    setup_logging(args.log_level)

    logging.info("Starting AvaxWhale Transaction Tracker")

    try:
        # Initialize blockchain connector and transaction analyzer
        connector = BlockchainConnector(args.config)
        analyzer = TransactionAnalyzer(connector)

        # Define a large transaction threshold (in USD)
        large_transaction_threshold = 10000  # Set your threshold here, e.g., $10,000

        # Read addresses from files
        address_categories = {
            'CEX': read_addresses_from_file('avalanche_eco/cexhotwallet.txt'),
            'DeFi': read_addresses_from_file('avalanche_eco/defi.txt'),
            'Stablecoins': read_addresses_from_file('avalanche_eco/stablecoins.txt'),
            'Meme': read_addresses_from_file('avalanche_eco/meme.txt'),
            'LST': read_addresses_from_file('avalanche_eco/lst.txt'),
            'Game': read_addresses_from_file('avalanche_eco/game.txt'),
            'Native': read_addresses_from_file('avalanche_eco/native.txt'),
            'DEX': read_addresses_from_file('avalanche_eco/dex.txt'),
            'TraderJoe': read_addresses_from_file('avalanche_eco/traderjoe.txt')
        }

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
    main()