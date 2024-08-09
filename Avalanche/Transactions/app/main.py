import sys
import os

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import argparse
import logging
import time
import json
from web3 import Web3
from blockchain.connector import BlockchainConnector
from blockchain.transactions import analyze_transaction
from utils.token_loader import EnhancedTokenLoader
from utils.routers import RouterLoader
from utils.wallets import WalletLoader
from datetime import datetime
from decimal import Decimal

def load_abi(erc_abis_dir, file_name):
    file_path = os.path.join(erc_abis_dir, file_name)
    try:
        with open(file_path, 'r') as file:
            abi = json.load(file)
        logging.info(f"Loaded ABI file: {file_name}")
        return abi
    except FileNotFoundError:
        logging.error(f"ABI file not found: {file_name}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding ABI file {file_name}: {e}")
        return None

def verify_directories(directories):
    """Ensure all necessary directories exist."""
    for directory in directories:
        if not os.path.exists(directory):
            logging.error(f"Directory does not exist: {directory}")
            return False
    return True

def verify_files(directory, filenames):
    """Ensure all necessary files exist."""
    for filename in filenames:
        file_path = os.path.join(directory, filename)
        if not os.path.exists(file_path):
            logging.error(f"File not found: {file_path}")
            return False
    return True

def setup_logging(log_level):
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

def track_transactions(args):
    setup_logging(args.log_level)
    logging.info("Starting Avalanche Transaction Tracker")

    try:
        connector = BlockchainConnector(args.config)
        large_transaction_threshold = Decimal('1000')  # Threshold for AVAX and token transactions in USD

        current_dir = os.path.dirname(os.path.abspath(__file__))
        utils_dir = os.path.join(current_dir, 'utils')
        router_abis_dir = os.path.join(current_dir, 'router_abis')
        erc_abis_dir = os.path.join(current_dir, 'erc')

        # Verify directories
        if not verify_directories([utils_dir, router_abis_dir, erc_abis_dir]):
            logging.error("Required directories are missing. Exiting.")
            return

        # Verify required files
        utils_files = ['cexhotwallet.txt', 'whales.txt', 'coins.txt', 'token_mapping.txt']
        expected_abi_files = [
            'uniswapv3router.json',
            'traderjoerouter.json',
            'traderjoelbrouterv21.json',
            '1inchnetworkrouter.json',
            '1inchnetworkaggregationrouterv5.json',
            'gmxpositionrouter.json',
            'lbrouter.json',
            'odosrouterv2.json'
        ]

        if not verify_files(utils_dir, utils_files):
            logging.error("Required utility files are missing. Exiting.")
            return

        if not verify_files(router_abis_dir, ['routers.txt'] + expected_abi_files):
            logging.error("Required router ABI files are missing. Exiting.")
            return

        # Initialize Web3
        w3 = Web3(Web3.HTTPProvider('https://api.avax.network/ext/bc/C/rpc'))

        # Load ABIs
        erc20_abi = load_abi(erc_abis_dir, 'erc20_abi.json')
        erc721_abi = load_abi(erc_abis_dir, 'erc721_abi.json')
        erc1155_abi = load_abi(erc_abis_dir, 'erc1155_abi.json')

        # Load tokens, routers, and wallets
        token_loader = EnhancedTokenLoader(utils_dir, w3, erc20_abi, erc721_abi, erc1155_abi)
        router_loader = RouterLoader(router_abis_dir)
        wallet_loader = WalletLoader(utils_dir)

        while True:
            try:
                transactions = connector.get_recent_transactions(block_count=10)
                logging.info(f"Fetched {len(transactions)} transactions")

                for tx in transactions:
                    logging.debug(f"Processing transaction: {tx['hash'].hex()}")
                    tx_timestamp = connector.w3.eth.get_block(tx['blockNumber'])['timestamp']
                    logging.debug(f"Transaction {tx['hash'].hex()} timestamp: {datetime.fromtimestamp(tx_timestamp)}")

                    analyze_transaction(
                        tx=tx,
                        w3=connector.w3,
                        threshold_usd=large_transaction_threshold,
                        avax_to_usd=connector.avax_to_usd,
                        token_loader=token_loader,
                        router_loader=router_loader,
                        wallet_loader=wallet_loader,
                        known_routers=router_loader.get_all_routers()
                    )

                time.sleep(args.interval)

            except Exception as e:
                logging.error(f"Error during monitoring: {str(e)}", exc_info=True)
                time.sleep(5)

    except Exception as e:
        logging.error(f"An error occurred during initialization: {str(e)}", exc_info=True)

    logging.info("Avalanche Transaction Tracker finished")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Avalanche Transaction Tracker")
    parser.add_argument("--config", required=True, help="Path to the configuration file")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    parser.add_argument("--interval", type=int, default=60, help="Interval between checks in seconds")
    args = parser.parse_args()

    track_transactions(args)