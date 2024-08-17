import logging
import os
import json
from web3 import Web3
from decimal import Decimal
from datetime import datetime

# Constants
BASE_PATH = os.path.join(os.path.dirname(__file__), '.', 'utils')

# Get the directory where the current script is located
current_directory = os.path.dirname(os.path.abspath(__file__))

# Construct the absolute path to the 'lbrouter.json' file
json_path = os.path.join(current_directory, 'lbrouter.json')

# Load the ABI from the JSON file
with open(json_path, 'r') as abi_file:
    LBROUTER = json.load(abi_file)

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

def analyze_lb_router_transaction(tx, w3, avax_to_usd, router_loader, token_loader):
    router_info = router_loader.get_router_info(tx['to'])
    if not router_info or router_info['name'] != 'LBRouter':
        return

    try:
        abi = router_info.get('abi')
        if not abi:
            logging.warning(f"Missing ABI for LBRouter: {tx['hash'].hex()}")
            return

        decoded_input = decode_transaction_input(w3, tx, abi)
        function_name, params = decoded_input


        log_lb_router_transaction(tx, router_info, function_name, params, w3, avax_to_usd, token_loader)

    except Exception as e:
        logging.error(f"Error analyzing LBRouter transaction {tx['hash'].hex()}: {str(e)}", exc_info=True)

def decode_transaction_input(w3, tx, abi):
    contract = w3.eth.contract(abi=LBROUTER)
    try:
        return contract.decode_function_input(tx['input'])
    except Exception as e:
        logging.error(f"Failed to decode transaction input: {e}")
        return None

def log_lb_router_transaction(tx, router_info, function_name, params, w3, avax_to_usd, token_loader):
    simplified_function_name = extract_function_name(function_name)
    
    logging.info("\n🔄 Trade/Exchange on %s\n", router_info['name'])
    
    logging.info("📊 Transaction Summary:")
    logging.info(f"🔗 Hash: {tx['hash'].hex()}")
    logging.info(f"⚙️ Function: {simplified_function_name}")
    logging.info(f"📍 Block: {tx['blockNumber']}\n")

    logging.info("💱 Swap Details:")
    if 'liquidityParameters' in params:
        log_liquidity_parameters(params['liquidityParameters'], token_loader)
    else:
        log_swap_details(simplified_function_name, params, token_loader, tx)

    logging.info("\n👤 Addresses:")
    logging.info(f"Sender: {tx['from']}")
    logging.info(f"Router: {tx['to']}\n")

    log_transaction_costs(tx, avax_to_usd)

    logging.info("====================================\n")

def log_liquidity_parameters(lp, token_loader):
    token_x = token_loader.get_token_info(lp['tokenX'])['label']
    token_y = token_loader.get_token_info(lp['tokenY'])['label']
    amount_x = Web3.from_wei(lp['amountX'], 'ether')
    amount_y = Web3.from_wei(lp['amountY'], 'ether')
    logging.info(f"Token X: {token_x} (Amount: {amount_x:.6f})")
    logging.info(f"Token Y: {token_y} (Amount: {amount_y:.6f})")
    logging.info(f"Bin Step: {lp['binStep']}")
    logging.info(f"Active ID Desired: {lp['activeIdDesired']}")
    logging.info(f"ID Slippage: {lp['idSlippage']}")
    logging.info(f"To: {lp['to']}")
    logging.info(f"Refund To: {lp['refundTo']}")
    logging.info(f"Deadline: {datetime.fromtimestamp(lp['deadline'])}")

def convert_token_amount(amount, token_address, token_loader):
    token_info = token_loader.get_token_info(token_address)
    decimals = token_info.get('details', {}).get('decimals', 18)  # Default to 18 if not specified
    return Decimal(amount) / Decimal(10 ** decimals)

def log_swap_details(function_name, params, token_loader, tx):
    path = params.get('path', {}).get('tokenPath', [])
    if not path:
        logging.warning("No token path found in parameters")
        return

    input_token_address = path[0]
    output_token_address = path[-1]
    input_token = token_loader.get_token_info(input_token_address)['label']
    output_token = token_loader.get_token_info(output_token_address)['label']

    if 'exactNATIVE' in function_name:
        input_amount = Web3.from_wei(tx['value'], 'ether')
    elif 'exact' in function_name.lower():
        input_amount = convert_token_amount(params.get('amountIn', 0), input_token_address, token_loader)
    else:
        input_amount = convert_token_amount(params.get('amountInMax', 0), input_token_address, token_loader)

    logging.info(f"Input Token: {input_token}")
    logging.info(f"Input Amount: {input_amount:.6f}")
    logging.info(f"Output Token: {output_token}")

    if 'exact' in function_name.lower() and 'NATIVE' not in function_name:
        output_amount = convert_token_amount(params.get('amountOut', 0), output_token_address, token_loader)
        logging.info(f"Output Amount: {output_amount:.6f} {output_token}")
    else:
        output_amount = convert_token_amount(params.get('amountOutMin', 0), output_token_address, token_loader)
        logging.info(f"Minimum Output Amount: {output_amount:.6f} {output_token}")

    
    logging.info(f"Path: {' -> '.join([token_loader.get_token_info(addr)['label'] for addr in path])}")
    logging.info(f"Recipient: {params.get('to', 'Unknown')}")
    if 'deadline' in params:
        logging.info(f"Deadline: {datetime.fromtimestamp(params['deadline'])}")

def log_transaction_costs(tx, avax_to_usd):
    value_avax = Web3.from_wei(tx['value'], 'ether')
    value_usd = float(value_avax) * avax_to_usd
    gas_price = Web3.from_wei(tx['gasPrice'], 'gwei')
    gas_cost_avax = gas_price * Decimal(tx['gas']) / Decimal(1e9)
    gas_cost_usd = float(gas_cost_avax) * avax_to_usd

    logging.info("💸 Transaction Cost:")
    logging.info(f"💰 Value: {value_avax:.4f} AVAX (${value_usd:.2f} USD)")
    logging.info(f"⛽ Gas: {gas_cost_avax:.6f} AVAX (${gas_cost_usd:.2f} USD)")

# Add any other LBRouter-specific functions here