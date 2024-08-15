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

# Construct the absolute path to the 'odos_router_V2.json' file
json_path = os.path.join(current_directory, 'pharaoh.json')

# Load the ABI from the JSON file
with open(json_path, 'r') as abi_file:
    PHAR = json.load(abi_file)

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
        function_name, params = decoded_input

        log_pharaoh_transaction(tx, router_info, function_name, params, w3, avax_to_usd, token_loader)

    except Exception as e:
        logging.error(f"Error analyzing Pharaoh transaction {tx['hash'].hex()}: {str(e)}")

def decode_transaction_input(w3, tx, abi):
    contract = w3.eth.contract(abi=PHAR)
    try:
        return contract.decode_function_input(tx['input'])
    except Exception as e:
        logging.error(f"Failed to decode transaction input: {e}")
        return None

def log_pharaoh_transaction(tx, router_info, function_name, params, w3, avax_to_usd, token_loader):
    logging.info("\n🔄 Trade/Exchange on %s\n", router_info['name'])
    logging.info("📊 Transaction Summary:")
    logging.info(f"🔗 Hash: {tx['hash'].hex()}")
    logging.info(f"⚙️ Function: {function_name}")
    logging.info(f"📍 Block: {tx['blockNumber']}\n")

    logging.info("💱 Swap Details:")
    
    if function_name == "swapCompact":
        log_pharaoh_swap_compact(params, token_loader, w3)
    else:
        logging.info(f"Unhandled function: {function_name}")

    logging.info("\n👤 Addresses:")
    logging.info(f"Sender: {tx['from']}")
    logging.info(f"Router: {tx['to']}")

    log_transaction_costs(tx, avax_to_usd)
    logging.info("====================================\n")

def log_pharaoh_swap_compact(params, token_loader, w3):
    path = params.get('path', [])
    if len(path) < 2:
        logging.warning("Invalid path length for swapCompact")
        return

    input_token = token_loader.get_token_info(path[0])
    output_token = token_loader.get_token_info(path[-1])
    
    input_amount = Web3.from_wei(params['amountIn'], 'ether')
    output_amount = Web3.from_wei(params['amountOutMin'], 'ether')

    logging.info(f"Input Token: {input_token['label']} ({path[0]})")
    logging.info(f"Input Amount: {input_amount:.6f}")
    logging.info(f"Output Token: {output_token['label']} ({path[-1]})")
    logging.info(f"Minimum Output Amount: {output_amount:.6f}")
    logging.info(f"Recipient: {params['to']}")
    logging.info(f"Deadline: {datetime.fromtimestamp(params['deadline'])}")

    if len(path) > 2:
        intermediate_tokens = [token_loader.get_token_info(addr)['label'] for addr in path[1:-1]]
        logging.info(f"Intermediate Tokens: {' -> '.join(intermediate_tokens)}")

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

def log_odos_swap_multi(params, token_loader):
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

def log_transaction_costs(tx, avax_to_usd):
    value_avax = Web3.from_wei(tx['value'], 'ether')
    value_usd = float(value_avax) * avax_to_usd
    gas_price = Web3.from_wei(tx['gasPrice'], 'gwei')
    gas_cost_avax = gas_price * Decimal(tx['gas']) / Decimal(1e9)
    gas_cost_usd = float(gas_cost_avax) * avax_to_usd

    logging.info("\n💸 Transaction Cost:")
    logging.info(f"💰 Value: {value_avax:.4f} AVAX (${value_usd:.2f} USD)")
    logging.info(f"⛽ Gas: {gas_cost_avax:.6f} AVAX (${gas_cost_usd:.2f} USD)")

# Add any other Odos-specific functions here if needed