import logging
import os
from web3 import Web3
from decimal import Decimal
from datetime import datetime

# Constants
BASE_PATH = os.path.join(os.path.dirname(__file__), '..', 'utils')

# Utility functions
def load_coins(filename="coins.txt"):
    file_path = os.path.join(BASE_PATH, filename)
    try:
        with open(file_path, "r") as file:
            return [line.strip() for line in file]
    except FileNotFoundError:
        logging.error(f"File {file_path} not found. Please check the path and try again.")
        return []

def calculate_transaction_value(tx, avax_to_usd):
    value_avax = Web3.from_wei(tx['value'], 'ether')
    value_usd = Decimal(value_avax) * Decimal(avax_to_usd)
    return value_avax, value_usd

def extract_function_name(function_object):
    if hasattr(function_object, 'function_identifier'):
        return function_object.function_identifier.split('(')[0]
    elif isinstance(function_object, str):
        return function_object.split('(')[0].split()[-1]
    else:
        return str(function_object).split('(')[0]

# Main analysis functions
def analyze_trade_or_exchange(tx, w3, avax_to_usd, router_loader, token_loader):
    router_info = router_loader.get_router_info(tx['to'])
    if not router_info:
        log_basic_transaction_info(tx, None, w3, avax_to_usd, token_loader)
        return

    try:
        abi = router_info.get('abi')
        if not abi:
            logging.warning(f"No ABI found for router {tx['to']}. Using basic analysis.")
            log_basic_transaction_info(tx, router_info, w3, avax_to_usd, token_loader)
            return

        decoded_input = decode_transaction_input(w3, tx, abi)
        if not decoded_input:
            raise ValueError("Failed to decode transaction input")

        log_decoded_transaction(tx, router_info, decoded_input, w3, avax_to_usd, token_loader)
    except Exception as e:
        logging.error(f"Error analyzing transaction {tx['hash'].hex()}: {str(e)}")
        log_basic_transaction_info(tx, router_info, w3, avax_to_usd, token_loader)

    log_transaction_flow(tx['hash'].hex(), w3, token_loader)

def decode_transaction_input(w3, tx, abi):
    contract = w3.eth.contract(abi=abi)
    try:
        return contract.decode_function_input(tx['input'])
    except Exception as e:
        logging.error(f"Failed to decode transaction input: {e}")
        return None


def log_decoded_transaction(tx, router_info, decoded_input, w3, avax_to_usd, token_loader):
    function_name, params = decoded_input

    logging.info("\n🔄 Trade/Exchange on %s\n", router_info['name'])
    
    logging.info("📊 Transaction Summary:")
    logging.info(f"🔗 Hash: {tx['hash'].hex()}")
    logging.info(f"⚙️ Function: {extract_function_name(function_name)}")
    logging.info(f"📍 Block: {tx['blockNumber']}\n")

    logging.info("💱 Swap Details:")
    if 'liquidityParameters' in params:
        lp = params['liquidityParameters']
        logging.info("Liquidity Parameters:")
        token_x = token_loader.get_token_info(lp['tokenX'])['label']
        token_y = token_loader.get_token_info(lp['tokenY'])['label']
        amount_x = Web3.from_wei(lp['amountX'], 'ether')
        amount_y = Web3.from_wei(lp['amountY'], 'ether')
        logging.info(f"  Token X: {token_x} (Amount: {amount_x:.6f})")
        logging.info(f"  Token Y: {token_y} (Amount: {amount_y:.6f})")
        logging.info(f"  Bin Step: {lp['binStep']}")
        logging.info(f"  Active ID Desired: {lp['activeIdDesired']}")
        logging.info(f"  ID Slippage: {lp['idSlippage']}")
        logging.info(f"  To: {lp['to']}")
        logging.info(f"  Refund To: {lp['refundTo']}")
        logging.info(f"  Deadline: {datetime.fromtimestamp(lp['deadline'])}")
    else:
        for key, value in params.items():
            if key == 'path':
                tokens = [token_loader.get_token_info(addr)['label'] for addr in value['tokenPath']]
                logging.info(f"Path: {' -> '.join(tokens)}")
            elif key in ['amountOutMin', 'amountOut']:
                amount = Web3.from_wei(value, 'ether')
                token = token_loader.get_token_info(params['path']['tokenPath'][-1])['label']
                logging.info(f"{key.capitalize()}: {amount:.6f} {token}")
            elif key == 'deadline':
                deadline_date = datetime.fromtimestamp(value)
                logging.info(f"Deadline: {deadline_date}")
            else:
                logging.info(f"{key.capitalize()}: {value}")
    logging.info("")

    logging.info("👤 Addresses:")
    logging.info(f"Sender: {tx['from']}")
    logging.info(f"Router: {tx['to']}\n")

    log_transaction_costs(tx, avax_to_usd)

    logging.info("====================================\n")

def log_transaction_costs(tx, avax_to_usd):
    value_avax = Web3.from_wei(tx['value'], 'ether')
    value_usd = float(value_avax) * avax_to_usd
    gas_price = Web3.from_wei(tx['gasPrice'], 'gwei')
    gas_cost_avax = gas_price * Decimal(tx['gas']) / Decimal(1e9)
    gas_cost_usd = float(gas_cost_avax) * avax_to_usd

    logging.info("💸 Transaction Cost:")
    logging.info(f"💰 Value: {value_avax:.4f} AVAX (${value_usd:.2f} USD)")
    logging.info(f"⛽ Gas: {gas_cost_avax:.6f} AVAX (${gas_cost_usd:.2f} USD)")


def log_basic_transaction_info(tx, router_info, w3, avax_to_usd, token_loader):
    value, value_usd = calculate_transaction_value(tx, avax_to_usd)
    
    to_token_info = token_loader.get_token_info(tx['to'])
    to_token = to_token_info['label'] if to_token_info else 'Unknown'
    
    logging.info("\n====================================")
    logging.info("💼 Basic Transaction Info:")
    logging.info(f"🔗 Hash: {tx['hash'].hex()}")
    logging.info(f"🏦 DEX: {router_info['name'] if router_info else 'Unknown'}")
    logging.info(f"📤 From: {tx['from']}")
    logging.info(f"📥 To: {tx['to']}")
    logging.info(f"💰 Value: {value:.4f} AVAX (${value_usd:.2f} USD)")
    logging.info(f"🔄 Possible Action: AVAX to {to_token}")
    logging.info("====================================\n")

def log_transaction_costs(tx, avax_to_usd):
    value_avax, value_usd = calculate_transaction_value(tx, avax_to_usd)
    gas_price = Web3.from_wei(tx['gasPrice'], 'gwei')
    gas_cost_avax = gas_price * Decimal(tx['gas']) / Decimal(1e9)
    gas_cost_usd = float(gas_cost_avax) * avax_to_usd

    logging.info("💸 Transaction Cost:")
    logging.info(f"💰 Value: {value_avax:.4f} AVAX (${value_usd:.2f} USD)")
    logging.info(f"⛽ Gas: {gas_cost_avax:.6f} AVAX (${gas_cost_usd:.2f} USD)\n")

def log_transaction_flow(tx_hash, w3, token_loader):
    try:
        tx_receipt = w3.eth.get_transaction_receipt(tx_hash)

        logging.info(f"🔗 Transaction Hash: {tx_hash}")
        logging.info("📊 Transaction Flow:")

        for log in tx_receipt.logs:
            try:
                token_address = log.get('address')
                if token_address:
                    token_info = token_loader.get_token_info(token_address)
                    token_symbol = token_info['label'] if token_info else 'Unknown Token'
                    
                    # Try to decode the 'data' field as an amount
                    amount = Web3.from_wei(int(log.get('data', '0'), 16), 'ether')
                    
                    # Check if 'topics' exists and has at least 3 elements
                    if 'topics' in log and len(log['topics']) >= 3:
                        from_address = Web3.to_checksum_address('0x' + log['topics'][1].hex()[-40:])
                        to_address = Web3.to_checksum_address('0x' + log['topics'][2].hex()[-40:])
                        
                        logging.info(f"🔄 Transfer: {amount} {token_symbol} from {from_address} to {to_address}")
                    else:
                        logging.info(f"🔄 Event: {amount} {token_symbol}")
            except Exception as e:
                logging.debug(f"Could not fully decode log entry: {str(e)}")

        logging.info("====================================\n")
    except Exception as e:
        logging.error(f"Error analyzing transaction flow for {tx_hash}: {str(e)}")