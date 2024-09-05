import logging
import os
import json
from web3 import Web3
from decimal import Decimal
from datetime import datetime, timedelta

# Constants and Configuration
BASE_PATH = os.path.join(os.path.dirname(__file__), '.', 'utils')
CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(CURRENT_DIRECTORY, 'lbrouter.json')

# Load ABI
with open(JSON_PATH, 'r') as abi_file:
    LBROUTER = json.load(abi_file)

# Utility Functions
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
    if hasattr(function_object, 'fn_name'):
        return function_object.fn_name
    elif hasattr(function_object, 'function_identifier'):
        return function_object.function_identifier.split('(')[0]
    elif isinstance(function_object, str):
        return function_object.split('(')[0].split()[-1]
    else:
        return str(function_object).split('(')[0]

def convert_token_amount(amount, token_address, token_loader):
    token_info = token_loader.get_token_info(token_address)
    decimals = token_info.get('decimals', 18)
    converted_amount = Decimal(amount) / Decimal(10 ** decimals)
    logging.debug(f"Raw Amount: {amount} | Decimals: {decimals} | Converted Amount: {converted_amount}")
    return converted_amount

# Main Transaction Analysis Function
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
        if not decoded_input:
            logging.error(f"Failed to decode transaction input for {tx['hash'].hex()}")
            return

        function_name, params = decoded_input
        log_lb_router_transaction(tx, router_info, function_name, params, w3, avax_to_usd, token_loader)

    except Exception as e:
        logging.error(f"Error analyzing LBRouter transaction {tx['hash'].hex()}: {str(e)}", exc_info=True)

def decode_transaction_input(w3, tx, abi):
    contract = w3.eth.contract(abi=abi)
    try:
        return contract.decode_function_input(tx['input'])
    except Exception as e:
        logging.error(f"Failed to decode transaction input: {e}")
        return None

# Logging Functions
def log_lb_router_transaction(tx, router_info, function_name, params, w3, avax_to_usd, token_loader):
    simplified_function_name = extract_function_name(function_name)
    
    logging.info("\n🔄 Trade/Exchange on %s\n", router_info['name'])
    logging.info("📊 Transaction Summary:")
    logging.info(f"🔗 Hash: {tx['hash'].hex()}")
    logging.info(f"⚙️ Function: {simplified_function_name}")
    logging.info(f"📍 Block: {tx['blockNumber']}\n")

    logging.info("💱 Transaction Details:")
    if 'liquidityParameters' in params:
        log_liquidity_parameters(params['liquidityParameters'], token_loader)
    elif simplified_function_name == 'removeLiquidity':
        log_remove_liquidity(params, token_loader)
    else:
        log_swap_details(simplified_function_name, params, token_loader, tx)

    logging.info("\n👤 Addresses:")
    logging.info(f"Sender: {tx['from']}")
    logging.info(f"Router: {tx['to']}\n")

    log_transaction_costs(tx, avax_to_usd)
    logging.info("====================================\n")

def log_remove_liquidity(params, token_loader):
    try:
        token_x = token_loader.get_token_info(params['tokenX'])['label']
        token_y = token_loader.get_token_info(params['tokenY'])['label']
        amount_x_min = Web3.from_wei(params['amountXMin'], 'ether')
        amount_y_min = Web3.from_wei(params['amountYMin'], 'ether')
        
        logging.info(f"Token X: {token_x}")
        logging.info(f"Token Y: {token_y}")
        logging.info(f"Minimum Amount X: {amount_x_min:.6f}")
        logging.info(f"Minimum Amount Y: {amount_y_min:.6f}")
        logging.info(f"Bin Step: {params['binStep']}")
        
        # Check if 'amountLiquidity' exists, otherwise use 'liquidity'
        if 'amountLiquidity' in params:
            logging.info(f"Amount Liquidity: {params['amountLiquidity']}")
        elif 'liquidity' in params:
            logging.info(f"Liquidity: {params['liquidity']}")
        else:
            logging.info("Liquidity information not available")
        
        logging.info(f"ID Slippage: {params['idSlippage']}")
        logging.info(f"Active ID Desired: {params['activeIdDesired']}")
        logging.info(f"To: {params['to']}")
        
        log_deadline(params.get('deadline'))
    except KeyError as e:
        logging.error(f"Missing expected parameter in remove_liquidity: {e}")
    except Exception as e:
        logging.error(f"Error in log_remove_liquidity: {e}")

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
    log_deadline(lp['deadline'])

def log_swap_details(function_name, params, token_loader, tx):
    path = params.get('path', {}).get('tokenPath', [])
    if not path:
        logging.warning("No token path found in parameters")
        return

    input_token_address = path[0]
    input_token = token_loader.get_token_info(input_token_address)
    if 'exactNATIVE' in function_name or input_token['label'] in ['WAVAX', 'AVAX']:
        input_amount = Web3.from_wei(tx['value'], 'ether')
    else:
        input_amount = convert_token_amount(params.get('amountIn', 0), input_token_address, token_loader)

    output_token_address = path[-1]
    output_token = token_loader.get_token_info(output_token_address)
    output_amount = convert_token_amount(params.get('amountOut', 0), output_token_address, token_loader)

    logging.info(f"Input Token: {input_token['label']}")
    logging.info(f"Input Amount: {input_amount:.6f} {input_token['label']}")
    logging.info(f"Output Token: {output_token['label']}")
    logging.info(f"Output Amount: {output_amount:.6f} {output_token['label']}")
    logging.info(f"Path: {' -> '.join([token_loader.get_token_info(addr)['label'] for addr in path])}")
    logging.info(f"Recipient: {params.get('to', 'Unknown')}")
    
    log_deadline(params.get('deadline'))

def log_transaction_costs(tx, avax_to_usd):
    value_avax = Web3.from_wei(tx['value'], 'ether')
    value_usd = float(value_avax) * avax_to_usd
    gas_price = Web3.from_wei(tx['gasPrice'], 'gwei')
    gas_cost_avax = gas_price * Decimal(tx['gas']) / Decimal(1e9)
    gas_cost_usd = float(gas_cost_avax) * avax_to_usd

    logging.info("💸 Transaction Cost:")
    logging.info(f"💰 Value: {value_avax:.4f} AVAX (${value_usd:.2f} USD)")
    logging.info(f"⛽ Gas: {gas_cost_avax:.6f} AVAX (${gas_cost_usd:.2f} USD)")

def log_deadline(deadline):
    if not deadline:
        return
    try:
        if deadline > 9999999999:  # Arbitrary large number to catch unreasonable values
            logging.info(f"Deadline: {deadline} (raw value, too large to convert)")
        else:
            deadline_dt = datetime.fromtimestamp(deadline)
            if deadline_dt > datetime.now() + timedelta(days=365):  # More than a year in the future
                logging.info(f"Deadline: {deadline_dt} (unusually far in the future)")
            else:
                logging.info(f"Deadline: {deadline_dt}")
    except (OSError, ValueError, OverflowError) as e:
        logging.warning(f"Invalid deadline value: {deadline}. Error: {str(e)}")

# Debug Function
def log_debug_info(message, data):
    logging.debug(f"DEBUG - {message}: {json.dumps(data, default=str)}")
