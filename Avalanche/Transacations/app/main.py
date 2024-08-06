import argparse
import logging
import time
from web3 import Web3
import requests
from blockchain.connector import BlockchainConnector
from blockchain.transactions import analyze_transaction
import os
import json
from datetime import datetime
from decimal import Decimal

def setup_logging(log_level):
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_arguments():
    parser = argparse.ArgumentParser(description="AvaxWhale Transaction Tracker")
    config_path = os.path.abspath('config/config.yaml')
    parser.add_argument("--config", default=config_path, help="Path to configuration file")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set the logging level")
    parser.add_argument("--interval", type=int, default=60, help="Interval in seconds between checks")
    return parser.parse_args()

def load_token_mappings(filepath):
    token_mappings = {}
    try:
        with open(filepath, 'r') as file:
            for line in file:
                line = line.strip()
                if line:
                    try:
                        address, token_name, pair_id = line.split(',', 2)
                        token_mappings[address.strip().lower()] = {
                            'name': token_name.strip(),
                            'pair_id': pair_id.strip(),
                            'contract_address': address.strip().lower()
                        }
                    except ValueError as e:
                        logging.error(f"Error parsing line '{line}' in token_mapping.txt: {e}")
    except FileNotFoundError as e:
        logging.error(f"Token mapping file not found: {e}")
    logging.debug(f"Loaded token mappings: {token_mappings}")
    return token_mappings

def fetch_dexscreener_data(pair_id, max_retries=3):
    url = f"https://api.dexscreener.com/latest/dex/pairs/avalanche/{pair_id}"
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if 'pair' in data and 'priceUsd' in data['pair']:
                return float(data['pair']['priceUsd'])
            else:
                logging.warning(f"Invalid response structure for pair {pair_id}: {data}")
                return None
        except requests.RequestException as e:
            logging.warning(f"Request failed for pair {pair_id} (Attempt {attempt + 1}/{max_retries}): {str(e)}")
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)
    logging.error(f"Failed to fetch data for pair {pair_id} after {max_retries} attempts")
    return None

def fetch_token_price(token_info):
    if token_info['pair_id']:
        return fetch_dexscreener_data(token_info['pair_id'])
    logging.warning(f"No pair ID available for token {token_info['name']}")
    return None

def track_transactions(args):
    setup_logging(args.log_level)
    logging.info("Starting AvaxWhale Transaction Tracker")

    try:
        connector = BlockchainConnector(args.config)
        large_transaction_threshold = Decimal('100')  # AVAX threshold in USD
        token_transaction_threshold = Decimal('10')   # Threshold for token transactions in USD

        current_dir = os.path.dirname(os.path.abspath(__file__))
        avalanche_eco_dir = os.path.join(current_dir, 'avalanche_eco')
        token_mapping_file = os.path.join(avalanche_eco_dir, 'token_mapping.txt')
        token_mappings = load_token_mappings(token_mapping_file)

        erc20_abi_file = os.path.join(avalanche_eco_dir, 'erc20_abi.json')
        with open(erc20_abi_file, 'r') as abi_file:
            erc20_abi = json.load(abi_file)

        while True:
            try:
                transactions = connector.get_recent_transactions(block_count=10)
                logging.info(f"Fetched {len(transactions)} transactions")
                logging.debug(f"Fetched transactions: {[tx['hash'].hex() for tx in transactions]}")

                for tx in transactions:
                    logging.debug(f"Processing transaction: {tx['hash'].hex()}")
                    tx_timestamp = connector.w3.eth.get_block(tx['blockNumber'])['timestamp']
                    logging.debug(f"Transaction {tx['hash'].hex()} timestamp: {datetime.fromtimestamp(tx_timestamp)}")

                    try:
                        tx_value_avax = Decimal(Web3.from_wei(tx['value'], 'ether'))
                        tx_value_usd = tx_value_avax * Decimal(str(connector.avax_to_usd))

                        if tx_value_usd >= large_transaction_threshold:
                            logging.info(f"Large transaction detected: Hash={tx['hash'].hex()}, "
                                         f"Value={tx_value_avax:.2f} AVAX, Value in USD={tx_value_usd:.2f}, "
                                         f"From={tx['from']}, To={tx['to']}")
                            # Pass avax_to_usd to the analyze_transaction function
                            analyze_transaction(tx, connector.w3, large_transaction_threshold, connector.avax_to_usd)
                        
                        # Check for token transactions
                        if tx['to'] and tx['to'].lower() in token_mappings:
                            token_address = Web3.to_checksum_address(tx['to'].lower())
                            token_info = token_mappings[tx['to'].lower()]
                            try:
                                contract = connector.w3.eth.contract(address=token_address, abi=erc20_abi)
                                decoded_input = contract.decode_function_input(tx['input'])
                                if decoded_input[0].fn_name in ['transfer', 'transferFrom']:
                                    token_amount = Decimal(Web3.from_wei(decoded_input[1].get('_value') or decoded_input[1].get('amount'), 'ether'))
                                    token_price_usd = fetch_token_price(token_info)
                                    if token_price_usd:
                                        tx_value_usd = token_amount * Decimal(str(token_price_usd))
                                        logging.debug(f"Token transaction detected: Hash={tx['hash'].hex()}, "
                                                      f"Token={token_info['name']}, Amount={token_amount:.2f}, "
                                                      f"Value in USD={tx_value_usd:.2f}")
                                        if tx_value_usd >= token_transaction_threshold:
                                            logging.info(f"Large token transaction detected: Hash={tx['hash'].hex()}, "
                                                         f"Token={token_info['name']}, Amount={token_amount:.2f}, "
                                                         f"Value in USD={tx_value_usd:.2f}, From={tx['from']}, "
                                                         f"To={decoded_input[1].get('_to') or decoded_input[1].get('to')}")
                            except Exception as e:
                                logging.error(f"Error decoding token transaction {tx['hash'].hex()}: {str(e)}")

                        # Check for swap transactions
                        if tx['input'].startswith(b'\x38\xed\x17\x39'):  # This is the function selector for 'swapExactTokensForTokens'
                            logging.info(f"Potential swap transaction detected: Hash={tx['hash'].hex()}, "
                                         f"From={tx['from']}, To={tx['to']}, Value={tx_value_avax:.6f} AVAX")

                    except Exception as tx_error:
                        logging.error(f"Error processing transaction {tx['hash'].hex()}: {str(tx_error)}")

                time.sleep(args.interval)

            except Exception as e:
                logging.error(f"Error during monitoring: {str(e)}", exc_info=True)
                time.sleep(5)

    except Exception as e:
        logging.error(f"An error occurred during initialization: {str(e)}", exc_info=True)

    logging.info("AvaxWhale Transaction Tracker finished")

if __name__ == "__main__":
    args = parse_arguments()
    track_transactions(args)