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
        log_pharaoh_swap_compact(params, token_loader, w3, tx)  # Add tx here
    else:
        logging.info(f"Unhandled function: {simplified_function_name}")

    logging.info("\n👤 Addresses:")
    logging.info(f"Sender: {tx['from']}")
    logging.info(f"Router: {tx['to']}")

    log_transaction_costs(tx, avax_to_usd)

    logging.info("====================================\n")

def log_pharaoh_swap_compact(params, token_loader, w3, tx):
    logging.debug(f"Swap Compact params: {params}")

    # Log initial input and final output if available
    if 'tokenX' in params and 'tokenY' in params:
        input_token = token_loader.get_token_info(params['tokenX'])['label']
        output_token = token_loader.get_token_info(params['tokenY'])['label']
        logging.info(f"Initial Input Token: {input_token}")
        logging.info(f"Final Output Token: {output_token}")

    # Log all token transfers from the transaction receipt
    receipt = w3.eth.get_transaction_receipt(tx['hash'])
    logging.info("Token Transfers:")
    for log in receipt.logs:
        if len(log['topics']) == 3 and log['topics'][0].hex() == '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef':
            from_address = '0x' + log['topics'][1].hex()[-40:]
            to_address = '0x' + log['topics'][2].hex()[-40:]
            token_address = log['address']

            # Try converting the 'data' value
            try:
                amount = Web3.from_wei(int(log['data'].hex(), 16), 'ether')
            except ValueError as e:
                logging.error(f"Error converting log data to int: {e}")
                logging.debug(f"Log data: {log['data']}")
                continue

            token_info = token_loader.get_token_info(token_address)
            token_symbol = token_info['label'] if token_info else 'Unknown Token'
            
            logging.info(f"  {amount:.6f} {token_symbol}")
            logging.info(f"    From: {from_address}")
            logging.info(f"    To: {to_address}")

    # Log detailed swap path if available
    if 'path' in params:
        logging.info("Detailed Swap Path:")
        for i, step in enumerate(params['path']):
            if isinstance(step, dict):
                router = step.get('router', 'Unknown Router')
                token_in = token_loader.get_token_info(step.get('tokenIn'))['label']
                token_out = token_loader.get_token_info(step.get('tokenOut'))['label']
                
                logging.info(f"  Step {i+1}: {router}")
                logging.info(f"    {token_in} -> {token_out}")
                
                # Log Uniswap V3 specific details if applicable
                uniswap_function, uniswap_params = decode_uniswap_v3_input(w3, step.get('data', '0x'))
                if uniswap_function:
                    log_uniswap_v3_params(uniswap_params, token_loader)
            elif isinstance(step, str):
                token_info = token_loader.get_token_info(step)
                logging.info(f"  Step {i+1}: {token_info['label']} ({step})")

    # Log additional parameters
    if 'to' in params:
        logging.info(f"Recipient: {params['to']}")
    if 'deadline' in params:
        logging.info(f"Deadline: {datetime.fromtimestamp(params['deadline'])}")
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
