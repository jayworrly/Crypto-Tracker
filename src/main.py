import argparse
import logging
import time
from pprint import pprint
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

        while True:
            try:
                # Fetch recent transactions
                transactions = connector.get_recent_transactions()

                # Analyze transactions
                analysis_results = analyzer.analyze_transactions(transactions)

                # Log the analysis results
                logging.info("Transaction Analysis Results:")
                pprint(analysis_results)

                # Highlight labeled transactions
                for label, txs in analysis_results["labeled_transactions"].items():
                    logging.info(f"Transactions for {label}:")
                    for tx in txs:
                        tx_value_avax = Web3.from_wei(tx['value'], 'ether')
                        tx_value_usd = float(tx_value_avax) * float(connector.avax_to_usd)
                        logging.info(f"Transaction to {label}: Hash={tx['hash'].hex()}, Value={tx_value_avax:.2f} AVAX, "
                                     f"Value in USD={tx_value_usd:.2f}, From={tx['from']}")

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
