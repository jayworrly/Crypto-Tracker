import os
import argparse
import logging
import time
import json
from web3 import Web3
from datetime import datetime
from decimal import Decimal
from web3.exceptions import ContractLogicError
from eth_abi.exceptions import InsufficientDataBytes
from blockchain.connector import BlockchainConnector
from blockchain.transactions import analyze_transaction
from utils.token_loader import EnhancedTokenLoader
from utils.routers import RouterLoader
from utils.wallets import WalletLoader

def load_abi(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error loading ABI file {file_path}: {e}")
        return None

def verify_paths(paths):
    for path in paths:
        if not os.path.exists(path):
            logging.error(f"Path does not exist: {path}")
            return False
    return True

def analyze_transaction_with_error_handling(tx, w3, threshold_usd, avax_to_usd, token_loader, router_loader, wallet_loader, known_routers):
    tx_hash = tx['hash'].hex()
    from_address = tx['from']
    to_address = tx['to']
    value = Web3.from_wei(tx['value'], 'ether')

    try:
        tx_analysis = analyze_transaction(tx, w3, threshold_usd, avax_to_usd, token_loader, router_loader, wallet_loader, known_routers)
        
        # Process transaction analysis results as needed
        
    except (ContractLogicError, InsufficientDataBytes) as e:
        logging.error(f"Contract interaction error for transaction {tx_hash}: {str(e)}")
        logging.error(f"Transaction details: From: {from_address}, To: {to_address}, Value: {value} AVAX")
        
        router_info = router_loader.get_router_info(to_address)
        if router_info:
            router_name = router_info['name']
            logging.error(f"Router info: {router_name}")
        else:
            logging.error("Transaction target is not a known router")
    except Exception as e:
        logging.error(f"Unexpected error analyzing transaction {tx_hash}: {str(e)}", exc_info=True)

def track_transactions(args):
    logging.basicConfig(level=args.log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("Starting Avalanche Transaction Tracker")

    try:
        connector = BlockchainConnector(args.config)
        large_transaction_threshold = Decimal('1000')

        current_dir = os.path.dirname(os.path.abspath(__file__))
        database_dir = os.path.join(current_dir, 'database')
        router_abis_dir = os.path.join(current_dir, 'blockchain', 'routers')
        erc_abis_dir = os.path.join(current_dir, 'erc')

        if not verify_paths([database_dir, router_abis_dir, erc_abis_dir]):
            return

        database_files = ['cexhotwallet.txt', 'whales.txt', 'coins.txt', 'routers.txt']
        expected_abi_files = [
            'traderjoe_lbrouterV2.json', 'gmx_position_router.json', 'lbrouter.json',
            'traderjoe.json', 'pangolin_exchange.json', "pharaoh.json"
        ]

        if not verify_paths([os.path.join(database_dir, f) for f in database_files] +
                            [os.path.join(router_abis_dir, f) for f in expected_abi_files]):
            return

        w3 = Web3(Web3.HTTPProvider('https://api.avax.network/ext/bc/C/rpc'))
        logging.info(f"Connected to Avalanche network: {w3.is_connected()}")

        erc20_abi = load_abi(os.path.join(erc_abis_dir, 'erc20_abi.json'))
        token_loader = EnhancedTokenLoader(database_dir, w3, erc20_abi)
        router_loader = RouterLoader(database_dir, router_abis_dir)
        wallet_loader = WalletLoader(database_dir)

        while True:
            try:
                transactions = connector.get_recent_transactions(block_count=10)

                for tx in transactions:
                    analyze_transaction_with_error_handling(
                        tx, connector.w3, large_transaction_threshold, connector.avax_to_usd,
                        token_loader, router_loader, wallet_loader, router_loader.get_all_routers()
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
    parser.add_argument("--interval", type=int, default=15, help="Interval between checks in seconds")
    args = parser.parse_args()

    track_transactions(args)