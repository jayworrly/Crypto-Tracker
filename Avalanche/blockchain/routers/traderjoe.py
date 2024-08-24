import os
import logging
import json
from web3 import Web3
from decimal import Decimal
from datetime import datetime

# Constants
BASE_PATH = os.path.join(os.path.dirname(__file__), '.', 'utils')

# Get the directory where the current script is located
current_directory = os.path.dirname(os.path.abspath(__file__))

# Construct the absolute path to the 'traderjoe.json' file
json_path = os.path.join(current_directory, 'traderjoe.json')

# Load the ABI from the JSON file
with open(json_path, 'r') as abi_file:
    TRADER_JOE_ABI = json.load(abi_file)

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

def analyze_traderjoe_router_transaction(tx, w3, avax_to_usd, router_loader, token_loader):
    router_info = router_loader.get_router_info(tx['to'])
    if not router_info or router_info['name'] != 'TraderJoe':
        return

    try:
        abi = router_info.get('abi')
        if not abi:
            logging.warning(f"Missing ABI for TradeJoe: {tx['hash'].hex()}")
            return

        decoded_input = decode_transaction_input(w3, tx, abi)
        function_name, params = decoded_input


        log_traderjoe_router_transaction(tx, router_info, function_name, params, w3, avax_to_usd, token_loader)

    except Exception as e:
        logging.error(f"Error analyzing LBRouter transaction {tx['hash'].hex()}: {str(e)}", exc_info=True)

def decode_transaction_input(w3, tx, abi):
    contract = w3.eth.contract(abi= TRADER_JOE_ABI)
    try:
        return contract.decode_function_input(tx['input'])
    except Exception as e:
        logging.error(f"Failed to decode transaction input: {e}")
        return None, None

def log_traderjoe_router_transaction(tx, router_info, function_name, params, w3, avax_to_usd, token_loader):
    simplified_function_name = extract_function_name(function_name)
    logging.info("\n🔄 Trade/Exchange on %s\n", router_info['name'])
    logging.info("📊 Transaction Summary:")
    logging.info(f"🔗 Hash: {tx['hash'].hex()}")
    logging.info(f"⚙️ Function: {simplified_function_name}")
    logging.info(f"📍 Block: {tx['blockNumber']}\n")
    if simplified_function_name.startswith('addLiquidity'):
        log_add_liquidity(simplified_function_name, params, token_loader)
    elif simplified_function_name.startswith('swap'):
        log_swap(simplified_function_name, params, token_loader, tx, avax_to_usd)
    elif simplified_function_name.startswith('removeLiquidity'):
        log_remove_liquidity(simplified_function_name, params, token_loader)
    else:
        logging.info(f"Unhandled function: {simplified_function_name}")
    logging.info("\n👤 Addresses:")
    logging.info(f"Sender: {tx['from']}")
    logging.info(f"Router: {tx['to']}")
    log_transaction_costs(tx, avax_to_usd)
    logging.info("====================================\n")

def convert_token_amount(amount, token_address, token_loader):
    try:
        token_info = token_loader.get_token_info(token_address)
        decimals = token_info.get('decimals', 18)  # Get decimals directly from token_info
        return Decimal(amount) / Decimal(10 ** decimals)
    except Exception as e:
        logging.error(f"Error in convert_token_amount: {str(e)}")
        logging.debug(f"Amount: {amount}, Token Address: {token_address}")
        return Decimal(0) 

def log_add_liquidity(function_name, params, token_loader):
    logging.info("Add Liquidity:")
    try:
        if 'AVAX' in function_name:
            token_a = 'AVAX'
            token_b_address = params.get('token', '')
            token_b = token_loader.get_token_info(token_b_address)
            amount_a = Web3.from_wei(params.get('msg.value', 0), 'ether')
            amount_b = convert_token_amount(params.get('amountTokenDesired', 0), token_b_address, token_loader)
        else:
            token_a_address = params.get('tokenA', '')
            token_b_address = params.get('tokenB', '')
            token_a = token_loader.get_token_info(token_a_address)
            token_b = token_loader.get_token_info(token_b_address)
            amount_a = convert_token_amount(params.get('amountADesired', 0), token_a_address, token_loader)
            amount_b = convert_token_amount(params.get('amountBDesired', 0), token_b_address, token_loader)
        
        logging.info(f"Token A: {token_a['label'] if isinstance(token_a, dict) else token_a}")
        logging.info(f"Amount A: {amount_a:.6f}")
        logging.info(f"Token B: {token_b['label'] if isinstance(token_b, dict) else 'Unknown'}")
        logging.info(f"Amount B: {amount_b:.6f}")
        logging.info(f"Recipient: {params.get('to', 'Unknown')}")
        deadline = params.get('deadline', 0)
        logging.info(f"Deadline: {datetime.fromtimestamp(deadline) if deadline else 'Unknown'}")
    except Exception as e:
        logging.error(f"Error in log_add_liquidity: {str(e)}")
        logging.debug(f"Function: {function_name}")
        logging.debug(f"Params: {params}")

def log_swap(function_name, params, token_loader, tx, avax_to_usd):
    logging.info("Swap Tokens:")
    path = params['path']
    input_token = token_loader.get_token_info(path[0])
    output_token = token_loader.get_token_info(path[-1])

    input_token_label = input_token['label']
    output_token_label = output_token['label']

    if function_name == 'swapExactAVAXForTokens':
        input_token_label = 'AVAX'
        input_amount = Web3.from_wei(tx['value'], 'ether')
        output_amount = convert_token_amount(params['amountOutMin'], path[-1], token_loader)
    elif function_name == 'swapAVAXForExactTokens':
        input_token_label = 'AVAX'
        input_amount = Web3.from_wei(tx['value'], 'ether')
        output_amount = convert_token_amount(params['amountOut'], path[-1], token_loader)
    elif function_name == 'swapExactTokensForAVAX':
        output_token_label = 'AVAX'
        input_amount = convert_token_amount(params['amountIn'], path[0], token_loader)
        output_amount = Web3.from_wei(params['amountOutMin'], 'ether')
    elif function_name == 'swapTokensForExactAVAX':
        output_token_label = 'AVAX'
        input_amount = convert_token_amount(params['amountInMax'], path[0], token_loader)
        output_amount = Web3.from_wei(params['amountOut'], 'ether')
    else:
        input_amount = convert_token_amount(params['amountIn'], path[0], token_loader)
        output_amount = convert_token_amount(params['amountOutMin'], path[-1], token_loader)

    logging.info(f"Input Token: {input_token_label}")
    logging.info(f"Input Amount: {input_amount:.6f}")
    logging.info(f"Output Token: {output_token_label}")
    logging.info(f"Output Amount: {output_amount:.6f}")
    logging.info(f"Recipient: {params['to']}")
    
    try:
        deadline = datetime.fromtimestamp(params['deadline'])
        logging.info(f"Deadline: {deadline}")
    except (OSError, ValueError, OverflowError) as e:
        logging.warning(f"Invalid deadline value: {params['deadline']}. Error: {str(e)}")
    
    logging.info(f"Path: {' -> '.join([token_loader.get_token_info(token)['label'] for token in path])}")
def log_remove_liquidity(function_name, params, token_loader):
    logging.info("Remove Liquidity:")
    token_a = token_loader.get_token_info(params['tokenA'])
    token_b = token_loader.get_token_info(params['tokenB'])
    
    if function_name.endswith('AVAX'):
        if token_a['label'] == 'WAVAX':
            token_a['label'] = 'AVAX'
        elif token_b['label'] == 'WAVAX':
            token_b['label'] = 'AVAX'
    
    amount_a = convert_token_amount(params['amountAMin'], params['tokenA'], token_loader)
    amount_b = convert_token_amount(params['amountBMin'], params['tokenB'], token_loader)
    
    logging.info(f"Token A: {token_a['label']}")
    logging.info(f"Amount A: {amount_a:.6f}")
    logging.info(f"Token B: {token_b['label']}")
    logging.info(f"Amount B: {amount_b:.6f}")
    logging.info(f"Recipient: {params['to']}")
    logging.info(f"Deadline: {datetime.fromtimestamp(params['deadline'])}")

def log_transaction_costs(tx, avax_to_usd):
    value_avax = Web3.from_wei(tx['value'], 'ether')
    value_usd = float(value_avax) * avax_to_usd
    gas_price = Web3.from_wei(tx['gasPrice'], 'gwei')
    gas_cost_avax = gas_price * Decimal(tx['gas']) / Decimal(1e9)
    gas_cost_usd = float(gas_cost_avax) * avax_to_usd

    logging.info("\n💸 Transaction Cost:")
    logging.info(f"💰 Value: {value_avax:.4f} AVAX (${value_usd:.2f} USD)")
    logging.info(f"⛽ Gas: {gas_cost_avax:.6f} AVAX (${gas_cost_usd:.2f} USD)")
