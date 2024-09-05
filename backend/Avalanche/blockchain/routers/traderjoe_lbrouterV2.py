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

# Construct the absolute path to the 'traderjoe_lbrouterV2.json' file
json_path = os.path.join(current_directory, 'traderjoe_lbrouterV2.json')

# Load the ABI from the JSON file
with open(json_path, 'r') as abi_file:
    TRADER_JOE = json.load(abi_file)


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

def analyze_traderjoe_v2_transaction(tx, w3, avax_to_usd, router_loader, token_loader):
    router_info = router_loader.get_router_info(tx['to'])
    if not router_info or router_info['name'] != 'TraderJoe LBRouterv2':
        return

    try:
        abi = router_info.get('abi')
        if not abi:
            logging.warning(f"Missing ABI for TraderJoe LBRouterV2: {tx['hash'].hex()}")
            return

        decoded_input = decode_transaction_input(w3, tx, abi)
        function_name, params = decoded_input

        log_traderjoe_v2_transaction(tx, router_info, function_name, params, w3, avax_to_usd, token_loader)

    except Exception as e:
        logging.error(f"Error analyzing TraderJoe LBRouterV2 transaction {tx['hash'].hex()}: {str(e)}")

def decode_transaction_input(w3, tx):
    contract = w3.eth.contract(abi=TRADER_JOE)
    try:
        return contract.decode_function_input(tx['input'])
    except Exception as e:
        logging.error(f"Failed to decode transaction input: {e}")
        return None

def log_traderjoe_v2_transaction(tx, router_info, function_name, params, w3, avax_to_usd, token_loader):
    simplified_function_name = extract_function_name(function_name)

    logging.info("\n🔄 Trade/Exchange on %s\n", router_info['name'])
    logging.info("📊 Transaction Summary:")
    logging.info(f"🔗 Hash: {tx['hash'].hex()}")
    logging.info(f"⚙️ Function: {function_name}")
    logging.info(f"📍 Block: {tx['blockNumber']}\n")

    logging.info("💱 Swap Details:")
    if function_name.startswith('swapExact'):
        log_traderjoe_v2_exact_swap(function_name, params, token_loader)
    elif function_name.startswith('swap') and 'ForExact' in function_name:
        log_traderjoe_v2_for_exact_swap(function_name, params, token_loader)
    elif function_name == 'addLiquidity' or function_name == 'addLiquidityNATIVE':
        log_traderjoe_v2_add_liquidity(function_name, params, token_loader)
    elif function_name == 'removeLiquidity' or function_name == 'removeLiquidityNATIVE':
        log_traderjoe_v2_remove_liquidity(function_name, params, token_loader)
    else:
        logging.info(f"Unhandled function: {simplified_function_name}")

    logging.info("\n👤 Addresses:")
    logging.info(f"Sender: {tx['from']}")
    logging.info(f"Router: {tx['to']}")

    log_transaction_costs(tx, avax_to_usd)

    logging.info("====================================\n")

def convert_token_amount(amount, token_address, token_loader):
    token_info = token_loader.get_token_info(token_address)
    decimals = token_info.get('details', {}).get('decimals', 18)  # Default to 18 if not specified
    return Decimal(amount) / Decimal(10 ** decimals)

def log_traderjoe_v2_exact_swap(function_name, params, token_loader):
    logging.info("Exact Input Swap:")
    path = params['path']
    input_token = token_loader.get_token_info(path['tokenPath'][0])['label']
    output_token = token_loader.get_token_info(path['tokenPath'][-1])['label']
    
    if 'NATIVE' in function_name:
        input_amount = Web3.from_wei(params['msg.value'], 'ether')
        input_token = 'AVAX'
    else:
        input_amount = convert_token_amount(params['amountIn'], path['tokenPath'][0], token_loader)
    
    output_amount = convert_token_amount(params['amountOutMin'], path['tokenPath'][-1], token_loader)
    
    logging.info(f"Input Token: {input_token}")
    logging.info(f"Input Amount: {input_amount:.6f}")
    logging.info(f"Output Token: {output_token}")
    logging.info(f"Minimum Output Amount: {output_amount:.6f}")
    logging.info(f"Recipient: {params['to']}")
    logging.info(f"Deadline: {datetime.fromtimestamp(params['deadline'])}")
    logging.info(f"Path: {' -> '.join([token_loader.get_token_info(token)['label'] for token in path['tokenPath']])}")

def log_traderjoe_v2_for_exact_swap(function_name, params, token_loader):
    logging.info("Exact Output Swap:")
    path = params['path']
    input_token = token_loader.get_token_info(path['tokenPath'][0])['label']
    output_token = token_loader.get_token_info(path['tokenPath'][-1])['label']
    
    if 'NATIVE' in function_name:
        if function_name.startswith('swapNATIVE'):
            input_token = 'AVAX'
            input_amount = Web3.from_wei(params['msg.value'], 'ether')
        else:
            output_token = 'AVAX'
            input_amount = convert_token_amount(params['amountInMax'], path['tokenPath'][0], token_loader)
    else:
        input_amount = convert_token_amount(params['amountInMax'], path['tokenPath'][0], token_loader)
    
    output_amount = convert_token_amount(params['amountOut'], path['tokenPath'][-1], token_loader)
    
    logging.info(f"Input Token: {input_token}")
    logging.info(f"Maximum Input Amount: {input_amount:.6f}")
    logging.info(f"Output Token: {output_token}")
    logging.info(f"Output Amount: {output_amount:.6f}")
    logging.info(f"Recipient: {params['to']}")
    logging.info(f"Deadline: {datetime.fromtimestamp(params['deadline'])}")
    logging.info(f"Path: {' -> '.join([token_loader.get_token_info(token)['label'] for token in path['tokenPath']])}")

def log_traderjoe_v2_add_liquidity(function_name, params, token_loader):
    logging.info("Add Liquidity:")
    lp = params['liquidityParameters']
    token_x = token_loader.get_token_info(lp['tokenX'])['label']
    token_y = token_loader.get_token_info(lp['tokenY'])['label']
    amount_x = Web3.from_wei(lp['amountX'], 'ether')
    amount_y = Web3.from_wei(lp['amountY'], 'ether')
    
    if function_name == 'addLiquidityNATIVE':
        if token_x == 'WAVAX':
            token_x = 'AVAX'
        elif token_y == 'WAVAX':
            token_y = 'AVAX'
    
    logging.info(f"Token X: {token_x}")
    logging.info(f"Amount X: {amount_x:.6f}")
    logging.info(f"Token Y: {token_y}")
    logging.info(f"Amount Y: {amount_y:.6f}")
    logging.info(f"Bin Step: {lp['binStep']}")
    logging.info(f"Active ID Desired: {lp['activeIdDesired']}")
    logging.info(f"ID Slippage: {lp['idSlippage']}")
    logging.info(f"Recipient: {lp['to']}")
    logging.info(f"Deadline: {datetime.fromtimestamp(lp['deadline'])}")

def log_traderjoe_v2_remove_liquidity(function_name, params, token_loader):
    logging.info("Remove Liquidity:")
    token_x = token_loader.get_token_info(params['tokenX'])['label']
    token_y = token_loader.get_token_info(params['tokenY'])['label']
    
    if function_name == 'removeLiquidityNATIVE':
        if token_x == 'WAVAX':
            token_x = 'AVAX'
        elif token_y == 'WAVAX':
            token_y = 'AVAX'
    
    logging.info(f"Token X: {token_x}")
    logging.info(f"Token Y: {token_y}")
    logging.info(f"Bin Step: {params['binStep']}")
    logging.info(f"Liquidity to Remove: {params['amounts']}")
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

# Add any other TraderJoe V2-specific functions here if needed