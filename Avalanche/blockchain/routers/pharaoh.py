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

# Construct the absolute path to the 'pharaoh.json' file
json_path = os.path.join(current_directory, 'pharaoh.json')

# Load the Pharaoh ABI from the JSON file
with open(json_path, 'r') as abi_file:
    PHAR = json.load(abi_file)

# Load the Uniswap V3 Pool ABI
uniswap_v3_json_path = os.path.join(current_directory, 'uniswapV3pool.json')
with open(uniswap_v3_json_path, 'r') as abi_file:
    UNISWAP_V3_POOL_ABI = json.load(abi_file)

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

def decode_uniswap_v3_input(w3, input_data):
    contract = w3.eth.contract(abi=UNISWAP_V3_POOL_ABI)
    try:
        decoded = contract.decode_function_input(input_data)
        return decoded[0].fn_name, decoded[1]
    except:
        return None, None

def analyze_pharaoh_transaction(tx, w3, avax_to_usd, router_loader, token_loader):
    router_info = router_loader.get_router_info(tx['to'])
    if not router_info or router_info['name'] != 'Pharaoh':
        return

    try:
        abi = router_info.get('abi')
        if not abi:
            logging.warning(f"Missing ABI for Pharaoh Router: {tx['hash'].hex()}")
            return

        decoded_input = decode_transaction_input(w3, tx, abi)
        if decoded_input:
            function_name, params = decoded_input
            log_pharaoh_transaction(tx, router_info, function_name, params, w3, avax_to_usd, token_loader)
        else:
            logging.warning(f"Failed to decode transaction input for {tx['hash'].hex()}")

    except Exception as e:
        logging.error(f"Error analyzing Pharaoh transaction {tx['hash'].hex()}: {str(e)}", exc_info=True)

def decode_transaction_input(w3, tx, abi):
    contract = w3.eth.contract(abi=PHAR)
    try:
        decoded = contract.decode_function_input(tx['input'])
        function_name = decoded[0].fn_name
        params = decoded[1]
        return function_name, params
    except Exception as e:
        logging.error(f"Failed to decode transaction input: {e}")
        return None

def log_pharaoh_transaction(tx, router_info, function_name, params, w3, avax_to_usd, token_loader):
    simplified_function_name = extract_function_name(function_name)

    logging.info("\n🔄 Trade/Exchange on %s\n", router_info['name'])
    logging.info("📊 Transaction Summary:")
    logging.info(f"🔗 Hash: {tx['hash'].hex()}")
    logging.info(f"⚙️ Function: {function_name}")
    logging.info(f"📍 Block: {tx['blockNumber']}\n")

    logging.info("💱 Swap Details:")
    
    if simplified_function_name == "swapCompact":
        log_pharaoh_swap_compact(params, token_loader, w3)
    else:
        logging.info(f"Unhandled function: {simplified_function_name}")

    logging.info("\n👤 Addresses:")
    logging.info(f"Sender: {tx['from']}")
    logging.info(f"Router: {tx['to']}")

    log_transaction_costs(tx, avax_to_usd)

    logging.info("====================================\n")

def log_pharaoh_swap_compact(params, token_loader, w3):
    # Log all parameters for debugging
    logging.debug(f"Swap Compact params: {params}")

    # Extract tokenX and tokenY addresses
    token_x = params.get('tokenX')
    token_y = params.get('tokenY')

    # Get token labels
    input_token = token_loader.get_token_info(token_x)['label'] if token_x else 'Unknown'
    output_token = token_loader.get_token_info(token_y)['label'] if token_y else 'Unknown'
    
    # Extract amounts
    amount_x_min = Web3.from_wei(params.get('amountXMin', 0), 'ether')
    amount_y_min = Web3.from_wei(params.get('amountYMin', 0), 'ether')

    logging.info(f"Input Token: {input_token}")
    logging.info(f"Output Token: {output_token}")
    logging.info(f"Minimum Input Amount: {amount_x_min:.6f}")
    logging.info(f"Minimum Output Amount: {amount_y_min:.6f}")
    logging.info(f"Recipient: {params.get('to', 'Unknown')}")

    if 'path' in params:
        logging.info("Detailed Swap Path:")
        for i, step in enumerate(params['path']):
            if isinstance(step, dict):
                router = step.get('router', 'Unknown Router')
                token_in = token_loader.get_token_info(step.get('tokenIn'))['label']
                token_out = token_loader.get_token_info(step.get('tokenOut'))['label']
                
                # Check if this step is a Uniswap V3 interaction
                uniswap_function, uniswap_params = decode_uniswap_v3_input(w3, step.get('data', '0x'))
                if uniswap_function:
                    logging.info(f"  Step {i+1}: Uniswap V3 Pool - {uniswap_function}")
                    logging.info(f"    {token_in} -> {token_out}")
                    log_uniswap_v3_params(uniswap_params, token_loader)
                else:
                    logging.info(f"  Step {i+1}: {router} - {token_in} -> {token_out}")
            elif isinstance(step, str):
                token_info = token_loader.get_token_info(step)
                logging.info(f"  Step {i+1}: {token_info['label']} ({step})")
    
    if 'deadline' in params:
        logging.info(f"Deadline: {datetime.fromtimestamp(params['deadline'])}")
    
    # Log any additional relevant parameters
    if 'binStep' in params:
        logging.info(f"Bin Step: {params['binStep']}")

def log_uniswap_v3_params(params, token_loader):
    if 'recipient' in params and 'zeroForOne' in params and 'amountSpecified' in params:
        direction = "Token0 to Token1" if params['zeroForOne'] else "Token1 to Token0"
        amount = Web3.from_wei(abs(int(params['amountSpecified'])), 'ether')
        logging.info(f"    Direction: {direction}")
        logging.info(f"    Amount Specified: {amount:.6f}")
        logging.info(f"    Recipient: {params['recipient']}")
        
        if 'sqrtPriceLimitX96' in params:
            sqrt_price_limit = int(params['sqrtPriceLimitX96'])
            logging.info(f"    Square Root Price Limit X96: {sqrt_price_limit}")
    else:
        logging.info("    Uniswap V3 swap details not fully available")

def log_transaction_costs(tx, avax_to_usd):
    value_avax = Web3.from_wei(tx['value'], 'ether')
    value_usd = float(value_avax) * avax_to_usd
    gas_price = Web3.from_wei(tx['gasPrice'], 'gwei')
    gas_cost_avax = gas_price * Decimal(tx['gas']) / Decimal(1e9)
    gas_cost_usd = float(gas_cost_avax) * avax_to_usd

    logging.info("\n💸 Transaction Cost:")
    logging.info(f"💰 Value: {value_avax:.4f} AVAX (${value_usd:.2f} USD)")
    logging.info(f"⛽ Gas: {gas_cost_avax:.6f} AVAX (${gas_cost_usd:.2f} USD)")

def log_pharaoh_swap(params, token_loader):
    token_info = params['tokenInfo']
    input_token = token_loader.get_token_info(token_info['inputToken'])['label']
    output_token = token_loader.get_token_info(token_info['outputToken'])['label']
    
    logging.info(f"Input Token: {input_token}")
    logging.info(f"Input Amount: {Web3.from_wei(token_info['inputAmount'], 'ether'):.6f}")
    logging.info(f"Output Token: {output_token}")
    logging.info(f"Output Quote: {Web3.from_wei(token_info['outputQuote'], 'ether'):.6f}")
    logging.info(f"Minimum Output: {Web3.from_wei(token_info['outputMin'], 'ether'):.6f}")
    logging.info(f"Input Receiver: {token_info['inputReceiver']}")
    logging.info(f"Output Receiver: {token_info['outputReceiver']}")

def log_pharaoh_swap_multi(params, token_loader):
    logging.info("Multi-Token Swap:")
    
    logging.info("Inputs:")
    for input_token in params['inputs']:
        token = token_loader.get_token_info(input_token['tokenAddress'])['label']
        logging.info(f"  Token: {token}")
        logging.info(f"  Amount: {Web3.from_wei(input_token['amountIn'], 'ether'):.6f}")
        logging.info(f"  Receiver: {input_token['receiver']}")
    
    logging.info("\nOutputs:")
    for output_token in params['outputs']:
        token = token_loader.get_token_info(output_token['tokenAddress'])['label']
        logging.info(f"  Token: {token}")
        logging.info(f"  Relative Value: {output_token['relativeValue']}")
        logging.info(f"  Receiver: {output_token['receiver']}")
    
    logging.info(f"\nMinimum Output Value: {Web3.from_wei(params['valueOutMin'], 'ether'):.6f}")
