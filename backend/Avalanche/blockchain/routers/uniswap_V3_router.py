import logging
import os
import json
from web3 import Web3
from decimal import Decimal
from datetime import datetime

# Get the directory where the current script is located
current_directory = os.path.dirname(os.path.abspath(__file__))

# Load ABIs
with open(os.path.join(current_directory, 'uniswapV3pool.json'), 'r') as abi_file:
    UNISWAP_V3_POOL_ABI = json.load(abi_file)

with open(os.path.join(current_directory, 'uniswap_V3_router.json'), 'r') as abi_file:
    UNISWAP_V3_ROUTER_ABI = json.load(abi_file)

def extract_function_name(function_object):
    if callable(function_object):
        return function_object.fn_name if hasattr(function_object, 'fn_name') else function_object.__name__
    elif isinstance(function_object, str):
        return function_object.split('(')[0].split()[-1]
    else:
        return str(function_object).split('(')[0]

def analyze_uniswap_v3_transaction(tx, w3, avax_to_usd, router_loader, token_loader):
    try:
        # Determine if it's a pool or router transaction
        if router_loader.get_router_info(tx['to']):
            contract = w3.eth.contract(address=tx['to'], abi=UNISWAP_V3_ROUTER_ABI)
        else:
            contract = w3.eth.contract(address=tx['to'], abi=UNISWAP_V3_POOL_ABI)
        
        decoded_input = contract.decode_function_input(tx['input'])
        function_name, params = decoded_input

        log_uniswap_v3_transaction(tx, function_name, params, w3, avax_to_usd, token_loader)

    except Exception as e:
        logging.error(f"Error analyzing Uniswap V3 transaction {tx['hash'].hex()}: {str(e)}")

def log_uniswap_v3_transaction(tx, function_name, params, w3, avax_to_usd, token_loader):
    simplified_function_name = extract_function_name(function_name)

    logging.info("\n🔄 Uniswap V3 Transaction (Avalanche)\n")
    logging.info("📊 Transaction Summary:")
    logging.info(f"🔗 Hash: {tx['hash'].hex()}")
    logging.info(f"⚙️ Function: {simplified_function_name}")
    logging.info(f"📍 Block: {tx['blockNumber']}\n")

    logging.info("💱 Transaction Details:")
    if simplified_function_name == 'swap':
        log_uniswap_v3_swap(params, token_loader)
    elif simplified_function_name == 'mint':
        log_uniswap_v3_add_liquidity(params, token_loader)
    elif simplified_function_name == 'burn':
        log_uniswap_v3_remove_liquidity(params, token_loader)
    elif simplified_function_name == 'execute':
        log_uniswap_v3_execute(params, token_loader, w3)  # Add w3 parameter here
    elif simplified_function_name == 'uniswapV3SwapCallback':
        log_uniswap_v3_swap_callback(params, token_loader)
    else:
        logging.info(f"Unhandled function: {simplified_function_name}")

    logging.info("\n👤 Addresses:")
    logging.info(f"Sender: {tx['from']}")
    logging.info(f"Contract: {tx['to']}")

    log_transaction_costs(tx, avax_to_usd)

    logging.info("====================================\n")

def convert_token_amount(amount, decimals):
    return Decimal(amount) / Decimal(10 ** decimals)

def log_uniswap_v3_swap(params, token_loader):
    logging.info("Swap:")
    recipient = params['recipient']
    zero_for_one = params['zeroForOne']
    amount_specified = Web3.from_wei(abs(int(params['amountSpecified'])), 'ether')
    sqrt_price_limit_x96 = params['sqrtPriceLimitX96']

    token0 = token_loader.get_token_info(params.get('token0'))
    token1 = token_loader.get_token_info(params.get('token1'))

    if token0 and token1:
        token_in = token0 if zero_for_one else token1
        token_out = token1 if zero_for_one else token0

        logging.info(f"Direction: {token_in['label']} -> {token_out['label']}")
        logging.info(f"Amount Specified: {amount_specified:.6f} {token_in['label']}")
    else:
        logging.info("Unable to determine token information")

    logging.info(f"Sqrt Price Limit X96: {sqrt_price_limit_x96}")
    logging.info(f"Recipient: {recipient}")


def log_uniswap_v3_add_liquidity(params, token_loader):
    logging.info("Add Liquidity:")
    recipient = params['recipient']
    tick_lower = params['tickLower']
    tick_upper = params['tickUpper']
    amount = params['amount']

    token_address = params.get('token') or params.get('tokenAddress')
    token_info = token_loader.get_token_info(token_address) if token_address else None
    
    if token_info:
        token_symbol = token_info['label']
        decimals = token_info['decimals']
        amount_converted = int(amount) / (10 ** decimals)
        logging.info(f"Amount: {amount_converted} {token_symbol}")
    else:
        logging.info(f"Amount: {amount} (Unknown Token)")

    logging.info(f"Recipient: {recipient}")
    logging.info(f"Tick Lower: {tick_lower}")
    logging.info(f"Tick Upper: {tick_upper}")


def log_uniswap_v3_remove_liquidity(params, token_loader):
    logging.info("Remove Liquidity:")
    tick_lower = params['tickLower']
    tick_upper = params['tickUpper']
    amount = params['amount']

    token_address = params.get('token') or params.get('tokenAddress')
    token_info = token_loader.get_token_info(token_address) if token_address else None
    
    if token_info:
        token_symbol = token_info['label']
        decimals = token_info['decimals']
        amount_converted = int(amount) / (10 ** decimals)
        logging.info(f"Amount: {amount_converted} {token_symbol}")
    else:
        logging.info(f"Amount: {amount} (Unknown Token)")

    logging.info(f"Tick Lower: {tick_lower}")
    logging.info(f"Tick Upper: {tick_upper}")

def log_uniswap_v3_execute(params, token_loader, w3):
    logging.info("Execute Transaction:")
    commands = params.get('commands', b'').hex()
    inputs = params.get('inputs', [])
    deadline = params.get('deadline', 0)

    logging.info(f"Commands: {commands}")
    logging.info(f"Number of inputs: {len(inputs)}")
    if deadline:
        logging.info(f"Deadline: {datetime.fromtimestamp(deadline)}")

    for i, input_data in enumerate(inputs):
        logging.info(f"Input {i}:")
        if isinstance(input_data, str) and input_data.startswith('0x'):
            # It's likely a hex string, convert to bytes
            input_data = bytes.fromhex(input_data[2:])
        
        if len(input_data) >= 4:  # Ensure there's at least a function selector
            function_selector = input_data[:4].hex()
            logging.info(f"  Function Selector: 0x{function_selector}")
            
            # Try to decode the rest of the input
            try:
                decoded = w3.eth.contract(abi=UNISWAP_V3_ROUTER_ABI).decode_function_input(input_data)
                logging.info(f"  Decoded Function: {decoded[0].fn_name}")
                for key, value in decoded[1].items():
                    if isinstance(value, bytes):
                        token_info = token_loader.get_token_info(value[:20])
                        if token_info:
                            logging.info(f"  {key}: {token_info['label']} ({value.hex()})")
                        else:
                            logging.info(f"  {key}: Unknown Token ({value.hex()})")
                    else:
                        logging.info(f"  {key}: {value}")
            except Exception as e:
                logging.warning(f"  Unable to decode input: {e}")
        
        logging.info(f"  Raw Data: {input_data.hex()}")

def log_uniswap_v3_swap_callback(params, token_loader):
    logging.info("Uniswap V3 Swap Callback:")
    amount0_delta = params['amount0Delta']
    amount1_delta = params['amount1Delta']
    data = params['data']

    token0_info = token_loader.get_token_info(data[:20]) if len(data) >= 20 else None
    token1_info = token_loader.get_token_info(data[20:40]) if len(data) >= 40 else None

    token0_symbol = token0_info['label'] if token0_info else 'Unknown Token'
    token1_symbol = token1_info['label'] if token1_info else 'Unknown Token'

    logging.info(f"Amount0 Delta: {amount0_delta} {token0_symbol}")
    logging.info(f"Amount1 Delta: {amount1_delta} {token1_symbol}")
    logging.info(f"Callback Data: {data.hex()}")


def log_transaction_costs(tx, avax_to_usd):
    value_avax = Web3.from_wei(tx['value'], 'ether')
    value_usd = float(value_avax) * avax_to_usd
    gas_price = Web3.from_wei(tx['gasPrice'], 'gwei')
    gas_cost_avax = gas_price * Decimal(tx['gas']) / Decimal(1e9)
    gas_cost_usd = float(gas_cost_avax) * avax_to_usd

    logging.info("💸 Transaction Cost:")
    logging.info(f"💰 Value: {value_avax:.4f} AVAX (${value_usd:.2f} USD)")
    logging.info(f"⛽ Gas: {gas_cost_avax:.6f} AVAX (${gas_cost_usd:.2f} USD)")