import logging
from web3 import Web3
import re
from decimal import Decimal
import os
from datetime import datetime

def load_coins(filename="coins.txt"):
    # Use the correct path from utils.coins
    base_path = os.path.join(os.path.dirname(__file__), '..', 'utils')
    file_path = os.path.join(base_path, filename)
    
    try:
        with open(file_path, "r") as file:
            coins = [line.strip() for line in file]
        return coins
    except FileNotFoundError:
        logging.error(f"File {file_path} not found. Please check the path and try again.")
        return []

# Utility function
def calculate_transaction_value(tx, avax_to_usd):
    value_avax = Web3.from_wei(tx['value'], 'ether')
    value_usd = Decimal(value_avax) * Decimal(avax_to_usd)
    return value_avax, value_usd

# Log intermediate transfers within the transaction
def log_intermediate_transfers(tx_receipt, w3, token_loader):
    for log in tx_receipt.logs:
        from_address = log['from']
        to_address = log['to']
        token_address = log['address']
        amount = w3.from_wei(log['data'], 'ether')

        token_info = token_loader.get_token_info(token_address)
        token_symbol = token_info['label'] if token_info else 'Unknown Token'

        logging.info(f"🔄 Transfer: {amount} {token_symbol} from {from_address} to {to_address}")

# Compare trade outcomes with coins in coins.txt
def check_trade_outcome(path, coins_list):
    for token_address in path:
        if token_address in coins_list:
            logging.info(f"💡 Trade involves a coin from your list: {token_address}")

def analyze_trade_or_exchange(tx, w3, avax_to_usd, router_loader, token_loader):
    router_info = router_loader.get_router_info(tx['to'])
    if router_info:
        try:
            abi = router_info.get('abi')
            if not abi:
                logging.warning(f"No ABI found for router {tx['to']}. Using basic analysis.")
                log_basic_transaction_info(tx, router_info, w3, avax_to_usd, token_loader)
                return

            try:
                decoded_input = decode_transaction_input(w3, tx, abi)
                if not decoded_input:
                    raise ValueError("Failed to decode transaction input")

                log_decoded_transaction(tx, router_info, decoded_input, w3, avax_to_usd, token_loader)
            except Exception as e:
                logging.warning(f"Error decoding or analyzing transaction {tx['hash'].hex()}: {str(e)}")
                log_basic_transaction_info(tx, router_info, w3, avax_to_usd, token_loader)
        except Exception as e:
            logging.error(f"Unexpected error analyzing transaction {tx['hash'].hex()}: {str(e)}")
            log_basic_transaction_info(tx, router_info, w3, avax_to_usd, token_loader)
    else:
        log_basic_transaction_info(tx, None, w3, avax_to_usd, token_loader)

    # Log the transaction flow through multiple contracts
    log_transaction_flow(tx['hash'].hex(), w3, token_loader)

def log_decoded_transaction(tx, router_info, decoded_input, w3, avax_to_usd, token_loader):
    params = decoded_input[1]
    path = params.get('path', [])
    
    # Get token symbols
    from_token = token_loader.get_token_info(path[0])
    to_token = token_loader.get_token_info(path[-1])
    via_token = token_loader.get_token_info(path[1]) if len(path) > 2 else None

    # Calculate amounts
    from_amount = Web3.from_wei(int(params.get('amountIn', 0)), 'ether')
    to_amount = Web3.from_wei(int(params.get('amountOutMin', 0)), 'ether')

    # Get block timestamp
    block = w3.eth.get_block(tx['blockNumber'])
    timestamp = datetime.fromtimestamp(block['timestamp'])

    logging.info("\n🔄 Trade/Exchange on %s\n", router_info['name'])
    
    logging.info("📊 Transaction Summary:")
    logging.info(f"🔗 Hash: {tx['hash'].hex()}")
    logging.info(f"🕒 Timestamp: {timestamp.strftime('%b-%d-%Y %I:%M:%S %p')} UTC")
    logging.info(f"📍 Block: {tx['blockNumber']}\n")

    logging.info("💱 Swap Details:")
    logging.info(f"From: {from_amount:.6f} {from_token['label']}")
    logging.info(f"To: {to_amount:.6f} {to_token['label']}")
    if via_token:
        logging.info(f"Via: [Amount not available] {via_token['label']}")
    logging.info("")

    logging.info("👤 Addresses:")
    logging.info(f"Sender: {tx['from']}")
    logging.info(f"Router: {tx['to']}\n")

    value_avax = Web3.from_wei(tx['value'], 'ether')
    value_usd = float(value_avax) * avax_to_usd
    gas_price = Web3.from_wei(tx['gasPrice'], 'gwei')
    gas_cost_avax = gas_price * Decimal(tx['gas']) / Decimal(1e9)
    gas_cost_usd = float(gas_cost_avax) * avax_to_usd

    logging.info("💸 Transaction Cost:")
    logging.info(f"💰 Value: {value_avax:.4f} AVAX (${value_usd:.2f} USD)")
    logging.info(f"⛽ Gas: {gas_cost_avax:.6f} AVAX (${gas_cost_usd:.2f} USD)\n")

    logging.info("🔍 Additional Info:")
    if len(path) > 2:
        logging.info(f"• Multi-hop swap: {' -> '.join([token_loader.get_token_info(t)['label'] for t in path])}")
    logging.info("• Used method supporting fee-on-transfer tokens")
    logging.info("====================================\n")

def decode_transaction_input(w3, tx, abi):
    contract = w3.eth.contract(abi=abi)
    try:
        decoded_input = contract.decode_function_input(tx['input'])
        return decoded_input
    except Exception as e:
        logging.error(f"Failed to decode transaction input: {e}")
        return None

def log_basic_transaction_info(tx, router_info, w3, avax_to_usd, token_loader):
    value = w3.from_wei(tx['value'], 'ether')
    value_usd = float(value) * avax_to_usd
    
    from_token = 'AVAX'
    to_token = 'Unknown'
    
    # Try to identify the 'to' token if it's a known contract
    to_token_info = token_loader.get_token_info(tx['to'])
    logging.info(f"  Token Info for 'To' Address: {to_token_info}")
    
    if to_token_info:
        to_token = to_token_info['label']
    else:
        logging.warning(f"No token information found for address {tx['to']}. Using 'Unknown'.")
    
    logging.info("\n====================================")
    logging.info("💼 Basic Transaction Info:")
    logging.info(f"🔗 Hash: {tx['hash'].hex()}")
    logging.info(f"🏦 DEX: {router_info['name'] if router_info else 'Unknown'}")
    logging.info(f"📤 From: {tx['from']}")
    logging.info(f"📥 To: {tx['to']}")
    logging.info(f"💰 Value: {value:.4f} AVAX (${value_usd:.2f} USD)")
    logging.info(f"🔄 Possible Action: {from_token} to {to_token}")
    logging.info("====================================\n")
    
def extract_function_name(function_object):
    if hasattr(function_object, 'function_identifier'):
        return function_object.function_identifier.split('(')[0]
    elif isinstance(function_object, str):
        return re.split(r'[\s(]', function_object)[0]
    else:
        return str(function_object).split('(')[0]
    
    # Log the transaction flow through multiple contracts
def log_transaction_flow(tx_hash, w3, token_loader):
    tx_receipt = w3.eth.get_transaction_receipt(tx_hash)

    logging.info(f"🔗 Transaction Hash: {tx_hash}")
    logging.info("📊 Transaction Flow:")

    log_intermediate_transfers(tx_receipt, w3, token_loader)

    logging.info("====================================\n")