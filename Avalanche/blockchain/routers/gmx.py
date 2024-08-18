import logging
import os
import json
from web3 import Web3
from decimal import Decimal
from datetime import datetime

# Get the directory where the current script is located
current_directory = os.path.dirname(os.path.abspath(__file__))

# Construct the absolute paths to the JSON files
GMX_ROUTER_ABI_PATH = os.path.join(current_directory, 'gmx_router.json')
GMX_POSITION_ROUTER_ABI_PATH = os.path.join(current_directory, 'gmx_position_router.json')

# Load the JSON files
try:
    with open(GMX_ROUTER_ABI_PATH, 'r') as abi_file:
        GMX_ROUTER_ABI = json.load(abi_file)
except FileNotFoundError:
    logging.error(f"ABI file not found: {GMX_ROUTER_ABI_PATH}")
    GMX_ROUTER_ABI = None

try:
    with open(GMX_POSITION_ROUTER_ABI_PATH, 'r') as abi_file:
        GMX_POSITION_ROUTER_ABI = json.load(abi_file)
except FileNotFoundError:
    logging.error(f"ABI file not found: {GMX_POSITION_ROUTER_ABI_PATH}")
    GMX_POSITION_ROUTER_ABI = None

def analyze_gmx_transaction(tx, w3, avax_to_usd, router_loader, token_loader):
    router_info = router_loader.get_router_info(tx['to'])
    if not router_info or (router_info['name'] != 'GMX Router' and router_info['name'] != 'GMX Position Router'):
        return

    try:
        abi = GMX_ROUTER_ABI if router_info['name'] == 'GMX Router' else GMX_POSITION_ROUTER_ABI
        if abi is None:
            logging.error(f"ABI not loaded for {router_info['name']}")
            return

        function_name, params = decode_transaction_input(w3, tx, abi)
        log_gmx_transaction(tx, router_info, function_name, params, w3, avax_to_usd, token_loader)
    except Exception as e:
        logging.error(f"Error analyzing GMX transaction {tx['hash'].hex()}: {str(e)}")

def decode_transaction_input(w3, tx, abi):
    contract = w3.eth.contract(address=tx['to'], abi=abi)
    return contract.decode_function_input(tx['input'])

def log_gmx_transaction(tx, router_info, function_name, params, w3, avax_to_usd, token_loader):
    logging.info(f"\n🔄 Trade/Exchange on {router_info['name']}")
    logging.info("📊 Transaction Summary:")
    logging.info(f"🔗 Hash: {tx['hash'].hex()}")
    logging.info(f"📍 Block: {tx['blockNumber']}")
    logging.info(f"⚙️ Function: {function_name}")

    if router_info['name'] == 'GMX Router':
        log_gmx_router_function(function_name, params, token_loader)
    elif router_info['name'] == 'GMX Position Router':
        log_gmx_position_router_function(function_name, params, token_loader)

    logging.info(f"\n👤 Sender: {tx['from']}")
    log_transaction_costs(tx, avax_to_usd)
    logging.info("====================================")

def log_gmx_router_function(function_name, params, token_loader):
    if "increasePosition" in function_name:
        log_increase_position(params, token_loader)
    elif "decreasePosition" in function_name:
        log_decrease_position(params, token_loader)
    elif "swap" in function_name:
        log_swap(params, token_loader)
    else:
        logging.info(f"Unhandled GMX Router function: {function_name}")
        logging.info(f"Parameters: {params}")

def log_gmx_position_router_function(function_name, params, token_loader):
    function_name_str = str(function_name)  # Convert function_name to a string

    if "createIncreasePosition" in function_name_str:
        log_create_increase_position(params, token_loader)
    elif "createDecreasePosition" in function_name_str:
        log_create_decrease_position(params, token_loader)
    elif "cancelIncreasePosition" in function_name_str:
        log_cancel_increase_position(params)
    elif "cancelDecreasePosition" in function_name_str:
        log_cancel_decrease_position(params)
    else:
        logging.info(f"Unhandled GMX Position Router function: {function_name_str}")
        logging.info(f"Parameters: {params}")


def convert_amount(amount, token_address, token_loader):
    token_info = token_loader.get_token_info(token_address)
    decimals = token_info.get('decimals', 18)  # Default to 18 if not specified
    return Decimal(amount) / Decimal(10 ** decimals)

def log_position_common(params, token_loader, position_type):
    path = params.get('_path', [])
    
    # Check if path is iterable
    if not isinstance(path, list):
        logging.error(f"Expected _path to be a list, but got {type(path).__name__}. Params: {params}")
        return
    
    path_labels = [token_loader.get_token_info(token)['label'] for token in path]
    logging.info(f"{position_type} Position:")
    logging.info(f"Path: {' -> '.join(path_labels)}")
    logging.info(f"Index Token: {token_loader.get_token_info(params['_indexToken'])['label']}")
    logging.info(f"Size Delta: {convert_amount(params['_sizeDelta'], params['_indexToken'], token_loader):.6f}")
    logging.info(f"Is Long: {params['_isLong']}")


def log_increase_position(params, token_loader):
    log_position_common(params, token_loader, "Increase")
    logging.info(f"Amount In: {convert_amount(params['_amountIn'], params['_path'][0], token_loader):.6f}")
    logging.info(f"Min Out: {convert_amount(params['_minOut'], params['_path'][-1], token_loader):.6f}")
    logging.info(f"Price: {convert_amount(params['_price'], params['_indexToken'], token_loader):.6f}")

def log_decrease_position(params, token_loader):
    log_position_common(params, token_loader, "Decrease")
    logging.info(f"Collateral Delta: {convert_amount(params['_collateralDelta'], params['_collateralToken'], token_loader):.6f}")
    logging.info(f"Receiver: {params['_receiver']}")
    logging.info(f"Price: {convert_amount(params['_price'], params['_indexToken'], token_loader):.6f}")

def log_swap(params, token_loader):
    logging.info("Swap:")
    path = [token_loader.get_token_info(token)['label'] for token in params['_path']]
    logging.info(f"Path: {' -> '.join(path)}")
    logging.info(f"Amount In: {convert_amount(params['_amountIn'], params['_path'][0], token_loader):.6f}")
    logging.info(f"Min Out: {convert_amount(params['_minOut'], params['_path'][-1], token_loader):.6f}")
    logging.info(f"Receiver: {params['_receiver']}")

def log_create_increase_position(params, token_loader):
    try:
        log_position_common(params, token_loader, "Create Increase")
        logging.info(f"Amount In: {convert_amount(params['_amountIn'], params['_path'][0], token_loader):.6f}")
        logging.info(f"Min Out: {convert_amount(params['_minOut'], params['_path'][-1], token_loader):.6f}")
        logging.info(f"Acceptable Price: {convert_amount(params['_acceptablePrice'], params['_indexToken'], token_loader):.6f}")
        logging.info(f"Execution Fee: {Web3.from_wei(params['_executionFee'], 'ether'):.6f} AVAX")
        logging.info(f"Referral Code: {params['_referralCode'].hex()}")
    except TypeError as e:
        logging.error(f"Error processing parameters: {e}")
        logging.info(f"Parameters: {params}")

def log_create_decrease_position(params, token_loader):
    log_position_common(params, token_loader, "Create Decrease")
    logging.info(f"Collateral Delta: {convert_amount(params['_collateralDelta'], params['_path'][0], token_loader):.6f}")
    logging.info(f"Receiver: {params['_receiver']}")
    logging.info(f"Acceptable Price: {convert_amount(params['_acceptablePrice'], params['_indexToken'], token_loader):.6f}")
    logging.info(f"Min Out: {convert_amount(params['_minOut'], params['_path'][-1], token_loader):.6f}")
    logging.info(f"Execution Fee: {Web3.from_wei(params['_executionFee'], 'ether'):.6f} AVAX")
    logging.info(f"Withdraw ETH: {params['_withdrawETH']}")

def log_cancel_increase_position(params):
    logging.info("Cancel Increase Position:")
    logging.info(f"Key: {params['_key'].hex()}")

def log_cancel_decrease_position(params):
    logging.info("Cancel Decrease Position:")
    logging.info(f"Key: {params['_key'].hex()}")

def log_transaction_costs(tx, avax_to_usd):
    value_avax = Web3.from_wei(tx['value'], 'ether')
    value_usd = float(value_avax) * avax_to_usd
    gas_price = Web3.from_wei(tx['gasPrice'], 'gwei')
    gas_cost_avax = gas_price * Decimal(tx['gas']) / Decimal(1e9)
    gas_cost_usd = float(gas_cost_avax) * avax_to_usd

    logging.info("\n💸 Transaction Cost:")
    logging.info(f"💰 Value: {value_avax:.4f} AVAX (${value_usd:.2f} USD)")
    logging.info(f"⛽ Gas: {gas_cost_avax:.6f} AVAX (${gas_cost_usd:.2f} USD)")