import sys
import os
import argparse
import logging
import time
import json
from web3 import Web3
from web3.exceptions import ContractLogicError
from eth_abi.exceptions import InsufficientDataBytes
from blockchain.connector import BlockchainConnector
from blockchain.transactions import analyze_transaction
from utils.token_loader import EnhancedTokenLoader
from utils.routers import RouterLoader
from utils.wallets import WalletLoader
from datetime import datetime
from decimal import Decimal

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_abi(erc_abis_dir, file_name):
    file_path = os.path.join(erc_abis_dir, file_name)
    logging.debug(f"Attempting to load ABI from: {file_path}")
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

def debug_contract_call(w3, tx, abi):
    """Attempt to decode the transaction input and provide debug information."""
    try:
        contract = w3.eth.contract(address=tx['to'], abi=abi)
        func_obj, func_params = contract.decode_function_input(tx['input'])
        logging.debug(f"Function called: {func_obj.fn_name}")
        logging.debug(f"Function parameters: {func_params}")
        
        # Attempt to call the function (read-only)
        result = func_obj.call(func_params)
        logging.debug(f"Function call result: {result}")
    except Exception as e:
        logging.error(f"Error in debug_contract_call: {str(e)}")

def analyze_transaction_with_error_handling(tx, w3, threshold_usd, avax_to_usd, token_loader, router_loader, wallet_loader, known_routers):
    try:
        analyze_transaction(
            tx=tx,
            w3=w3,
            threshold_usd=threshold_usd,
            avax_to_usd=avax_to_usd,
            token_loader=token_loader,
            router_loader=router_loader,
            wallet_loader=wallet_loader,
            known_routers=known_routers
        )
    except (ContractLogicError, InsufficientDataBytes) as e:
        logging.error(f"Contract interaction error for transaction {tx['hash'].hex()}: {str(e)}")
        logging.error(f"Transaction details: From: {tx['from']}, To: {tx['to']}, Value: {Web3.from_wei(tx['value'], 'ether')} AVAX")
        
        router_info = router_loader.get_router_info(tx['to'])
        if router_info:
            logging.error(f"Router info: {router_info['name']}")
            debug_contract_call(w3, tx, router_info['abi'])
        else:
            logging.error("Transaction target is not a known router")
        
        # Check if the contract exists
        code = w3.eth.get_code(tx['to'])
        if code == b'':
            logging.error("Contract does not exist at the given address")
        else:
            logging.debug("Contract exists at the given address")
        
        # Check network status
        try:
            latest_block = w3.eth.get_block('latest')
            logging.debug(f"Latest block: {latest_block.number}, timestamp: {datetime.fromtimestamp(latest_block.timestamp)}")
        except Exception as block_error:
            logging.error(f"Error fetching latest block: {str(block_error)}")

    except Exception as e:
        logging.error(f"Unexpected error analyzing transaction {tx['hash'].hex()}: {str(e)}", exc_info=True)

def track_transactions(args):
    setup_logging(args.log_level)
    logging.info("Starting Avalanche Transaction Tracker")
    logging.debug(f"Current working directory: {os.getcwd()}")

    try:
        connector = BlockchainConnector(args.config)
        large_transaction_threshold = Decimal('1000')  # Threshold for AVAX and token transactions in USD

        current_dir = os.path.dirname(os.path.abspath(__file__))
        database_dir = os.path.join(current_dir, 'database')
        router_abis_dir = os.path.join(current_dir, 'blockchain', 'routers')
        erc_abis_dir = os.path.join(current_dir, 'erc')

        logging.debug(f"Database directory: {database_dir}")
        logging.debug(f"Router ABIs directory: {router_abis_dir}")
        logging.debug(f"ERC ABIs directory: {erc_abis_dir}")

        # Verify directories
        if not verify_directories([database_dir, router_abis_dir, erc_abis_dir]):
            logging.error("Required directories are missing. Exiting.")
            return

        # Verify required files
        database_files = ['cexhotwallet.txt', 'whales.txt', 'coins.txt', 'token_mapping.txt', 'routers.txt']
        expected_abi_files = [
            'traderjoe_lbrouterV2.json',
            'gmx_position_router.json',
            'lbrouter.json',
            'traderjoe.json',
            'pangolin_exchange.json',
            "pharaoh.json"
        ]

        if not verify_files(database_dir, database_files):
            logging.error("Required database files are missing. Exiting.")
            return

        if not verify_files(router_abis_dir, expected_abi_files):
            logging.error("Required router ABI files are missing. Exiting.")
            return

        # Initialize Web3
        w3 = Web3(Web3.HTTPProvider('https://api.avax.network/ext/bc/C/rpc'))
        logging.info(f"Connected to Avalanche network: {w3.is_connected()}")

        # Load ABIs
        erc20_abi = load_abi(erc_abis_dir, 'erc20_abi.json')
        erc721_abi = load_abi(erc_abis_dir, 'erc721_abi.json')
        erc1155_abi = load_abi(erc_abis_dir, 'erc1155_abi.json')

        # Load tokens, routers, and wallets
        token_loader = EnhancedTokenLoader(database_dir, w3, erc20_abi, erc721_abi, erc1155_abi)
        router_loader = RouterLoader(database_dir, router_abis_dir)
        wallet_loader = WalletLoader(database_dir)

        while True:
            try:
                transactions = connector.get_recent_transactions(block_count=10)
                logging.info(f"Fetched {len(transactions)} transactions")

                for tx in transactions:
                    logging.debug(f"Processing transaction: {tx['hash'].hex()}")
                    tx_timestamp = connector.w3.eth.get_block(tx['blockNumber'])['timestamp']
                    logging.debug(f"Transaction {tx['hash'].hex()} timestamp: {datetime.fromtimestamp(tx_timestamp)}")

                    analyze_transaction_with_error_handling(
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
    parser.add_argument("--log-level", default="DEBUG", help="Logging level")
    parser.add_argument("--interval", type=int, default=15, help="Interval between checks in seconds")
    args = parser.parse_args()

    track_transactions(args)