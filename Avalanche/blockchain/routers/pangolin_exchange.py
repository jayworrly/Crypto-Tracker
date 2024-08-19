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

# Construct the absolute path to the 'pangolin_router.json' file
json_path = os.path.join(current_directory, 'pangolin_exchange.json')

# Load the ABI from the JSON file
with open(json_path, 'r') as abi_file:
    PANGOLIN = json.load(abi_file)

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
    if callable(function_object):
        return function_object.fn_name if hasattr(function_object, 'fn_name') else function_object.__name__
    elif isinstance(function_object, str):
        return function_object.split('(')[0].split()[-1]
    else:
        return str(function_object).split('(')[0]
    
def analyze_pangolin_transaction(tx, w3, avax_to_usd, router_loader, token_loader):
    router_info = router_loader.get_router_info(tx['to'])
    if not router_info or router_info['name'] != 'Pangolin Exchange':
        return

    try:
        abi = router_info.get('abi')
        if not abi:
            logging.warning(f"Missing ABI for Pangolin Exchange: {tx['hash'].hex()}")
            return

        decoded_input = decode_transaction_input(w3, tx, abi)
        function_name, params = decoded_input

        log_pangolin_transaction(tx, router_info, function_name, params, w3, avax_to_usd, token_loader)

    except Exception as e:
        logging.error(f"Error analyzing Pangolin transaction {tx['hash'].hex()}: {str(e)}")

def decode_transaction_input(w3, tx, abi):
    contract = w3.eth.contract(abi=PANGOLIN)
    try:
        return contract.decode_function_input(tx['input'])
    except Exception as e:
        logging.error(f"Failed to decode transaction input: {e}")
        return None

def log_pangolin_transaction(tx, router_info, function_name, params, w3, avax_to_usd, token_loader):
    simplified_function_name = extract_function_name(function_name)

    logging.info("\n🔄 Trade/Exchange on %s\n", router_info['name'])  
    logging.info("📊 Transaction Summary:")
    logging.info(f"🔗 Hash: {tx['hash'].hex()}")
    logging.info(f"⚙️ Function: {simplified_function_name}")
    logging.info(f"📍 Block: {tx['blockNumber']}\n")

    logging.info("💱 Swap Details:")
    if simplified_function_name.startswith('swapExact'):
        log_pangolin_exact_swap(simplified_function_name, params, token_loader)
    elif simplified_function_name.startswith('swap') and 'ForExact' in simplified_function_name:
        log_pangolin_for_exact_swap(simplified_function_name, params, token_loader)
    elif simplified_function_name.startswith('add'):
        log_pangolin_add_liquidity(simplified_function_name, params, token_loader)
    elif simplified_function_name.startswith('remove'):
        log_pangolin_remove_liquidity(simplified_function_name, params, token_loader)
    else:
        logging.info(f"Unhandled function: {simplified_function_name}")

    logging.info("\n👤 Addresses:")
    logging.info(f"Sender: {tx['from']}")
    logging.info(f"Router: {tx['to']}")

    log_transaction_costs(tx, avax_to_usd)

    logging.info("====================================\n")

def convert_token_amount(amount, token_address, token_loader):
    token_info = token_loader.get_token_info(token_address)
    decimals = token_info.get('decimals', 18)  # Get decimals directly from token_info
    return Decimal(amount) / Decimal(10 ** decimals)

def log_pangolin_exact_swap(function_name, params, token_loader):
    logging.info("Exact Input Swap:")
    if 'AVAX' in function_name:
        input_token = 'AVAX'
        if 'msg.value' in params:
            input_amount = Web3.from_wei(params['msg.value'], 'ether')
        else:
            logging.error("msg.value is missing from transaction parameters")
            return
    else:
        input_token = token_loader.get_token_info(params['path'][0])['label']
        input_amount = convert_token_amount(params['amountIn'], params['path'][0], token_loader)
    
    output_token = token_loader.get_token_info(params['path'][-1])['label']
    output_amount = convert_token_amount(params['amountOutMin'], params['path'][-1], token_loader)
    
    logging.info(f"Input Token: {input_token}")
    logging.info(f"Input Amount: {input_amount:.6f}")
    logging.info(f"Output Token: {output_token}")
    logging.info(f"Minimum Output Amount: {output_amount:.6f}")
    logging.info(f"Recipient: {params['to']}")
    logging.info(f"Deadline: {datetime.fromtimestamp(params['deadline'])}")

def log_pangolin_for_exact_swap(function_name, params, token_loader):
    logging.info("Exact Output Swap:")
    if 'AVAX' in function_name:
        output_token = 'AVAX'
    else:
        output_token = token_loader.get_token_info(params['path'][-1])['label']
    
    input_token = token_loader.get_token_info(params['path'][0])['label']
    
    if 'amountInMax' in params:
        input_amount = convert_token_amount(params['amountInMax'], params['path'][0], token_loader)
    else:
        logging.error("amountInMax is missing from transaction parameters")
        return

    output_amount = convert_token_amount(params['amountOut'], params['path'][-1], token_loader)
    
    logging.info(f"Input Token: {input_token}")
    logging.info(f"Maximum Input Amount: {input_amount:.6f}")
    logging.info(f"Output Token: {output_token}")
    logging.info(f"Output Amount: {output_amount:.6f}")
    logging.info(f"Recipient: {params['to']}")
    logging.info(f"Deadline: {datetime.fromtimestamp(params['deadline'])}")

def log_pangolin_add_liquidity(function_name, params, token_loader):
    logging.info("Add Liquidity:")
    if 'AVAX' in function_name:
        token_a = 'AVAX'
        token_b = token_loader.get_token_info(params['token'])
        amount_a = Web3.from_wei(params['msg.value'], 'ether')
        amount_b = convert_token_amount(params['amountTokenDesired'], params['token'], token_loader)
    else:
        token_a = token_loader.get_token_info(params['tokenA'])
        token_b = token_loader.get_token_info(params['tokenB'])
        amount_a = convert_token_amount(params['amountADesired'], params['tokenA'], token_loader)
        amount_b = convert_token_amount(params['amountBDesired'], params['tokenB'], token_loader)
    
    logging.info(f"Token A: {token_a['label'] if isinstance(token_a, dict) else token_a}")
    logging.info(f"Amount A: {amount_a:.6f}")
    logging.info(f"Token B: {token_b['label']}")
    logging.info(f"Amount B: {amount_b:.6f}")
    logging.info(f"Recipient: {params['to']}")
    logging.info(f"Deadline: {datetime.fromtimestamp(params['deadline'])}")

def log_pangolin_remove_liquidity(function_name, params, token_loader):
    logging.info("Remove Liquidity:")
    if 'AVAX' in function_name:
        token_a = 'AVAX'
        token_b = token_loader.get_token_info(params['token'])
    else:
        token_a = token_loader.get_token_info(params['tokenA'])
        token_b = token_loader.get_token_info(params['tokenB'])
    
    liquidity = Web3.from_wei(params['liquidity'], 'ether')
    
    logging.info(f"Token A: {token_a['label'] if isinstance(token_a, dict) else token_a}")
    logging.info(f"Token B: {token_b['label']}")
    logging.info(f"Liquidity to Remove: {liquidity:.6f}")
    logging.info(f"Recipient: {params['to']}")
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

# Add any other Pangolin-specific functions here if needed