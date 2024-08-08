import logging
from web3 import Web3
import re

def analyze_trade_or_exchange(tx, w3, avax_to_usd, router_loader, token_loader):
    """Analyze and log trades or exchanges."""
    router_info = router_loader.get_router_info(tx['to'])
    if router_info:
        try:
            abi = router_info.get('abi')
            if not abi:
                logging.warning(f"No ABI found for router {tx['to']}. Skipping detailed analysis.")
                return

            contract = w3.eth.contract(address=tx['to'], abi=abi)
            
            try:
                decoded_input = contract.decode_function_input(tx['input'])
            except ValueError as e:
                if "Could not find any function with matching selector" in str(e):
                    selector = tx['input'][:10]
                    logging.warning(f"Unknown function selector {selector} for transaction {tx['hash'].hex()}. This might be a new or custom function.")
                    log_basic_transaction_info(tx, router_info, w3, avax_to_usd)
                    return
                raise
            
            log_decoded_transaction(tx, router_info, decoded_input, w3, avax_to_usd, token_loader)
        except Exception as e:
            logging.error(f"Error decoding trade/exchange transaction {tx['hash'].hex()}: {str(e)}")
            log_basic_transaction_info(tx, router_info, w3, avax_to_usd)

def log_basic_transaction_info(tx, router_info, w3, avax_to_usd):
    value = w3.from_wei(tx['value'], 'ether')
    value_usd = float(value) * avax_to_usd
    logging.info("\n====================================")
    logging.info("Basic Transaction Info:")
    logging.info(f"  Hash: {tx['hash'].hex()}")
    logging.info(f"  DEX: {router_info['name']}")
    logging.info(f"  From: {tx['from']}")
    logging.info(f"  To: {tx['to']}")
    logging.info(f"  Value: {value:.4f} AVAX (${value_usd:.2f} USD)")
    logging.info("====================================\n")

def log_decoded_transaction(tx, router_info, decoded_input, w3, avax_to_usd, token_loader):
    logging.info("\n====================================")
    logging.info("Trade/Exchange Detected:")
    logging.info(f"  Hash: {tx['hash'].hex()}")
    logging.info(f"  DEX: {router_info['name']}")
    
    # Extract only the function name without parameters
    function_name = extract_function_name(decoded_input[0])
    logging.info(f"  Function: {function_name}")
    
    if 'swap' in function_name.lower():
        log_swap_details(decoded_input, w3, token_loader)
    elif 'addLiquidity' in function_name:
        log_add_liquidity_details(decoded_input, w3, token_loader)
    elif 'removeLiquidity' in function_name:
        log_remove_liquidity_details(decoded_input, w3, token_loader)
    else:
        log_generic_function_details(decoded_input, w3)
    
    logging.info("====================================\n")

def extract_function_name(function_object):
    if hasattr(function_object, 'function_identifier'):
        # Extract only the function name from the identifier
        return function_object.function_identifier.split('(')[0]
    elif isinstance(function_object, str):
        # If it's already a string, extract the function name
        return re.split(r'[\s(]', function_object)[0]
    else:
        # Fallback to string representation if we can't extract the name
        return str(function_object).split('(')[0]

def log_swap_details(decoded_input, w3, token_loader):
    path = decoded_input[1].get('path', [])
    if len(path) >= 2:
        from_token = token_loader.get_token_info(path[0])
        to_token = token_loader.get_token_info(path[-1])
        logging.info(f"  From Token: {from_token['label'] if from_token else path[0]}")
        logging.info(f"  To Token: {to_token['label'] if to_token else path[-1]}")
    
    amount_in = decoded_input[1].get('amountIn') or decoded_input[1].get('amountInMax')
    amount_out = decoded_input[1].get('amountOut') or decoded_input[1].get('amountOutMin')
    if amount_in:
        logging.info(f"  Amount In: {w3.from_wei(amount_in, 'ether')}")
    if amount_out:
        logging.info(f"  Amount Out: {w3.from_wei(amount_out, 'ether')}")

def log_add_liquidity_details(decoded_input, w3, token_loader):
    token_a = token_loader.get_token_info(decoded_input[1].get('tokenA'))
    token_b = token_loader.get_token_info(decoded_input[1].get('tokenB'))
    logging.info(f"  Token A: {token_a['label'] if token_a else decoded_input[1].get('tokenA')}")
    logging.info(f"  Token B: {token_b['label'] if token_b else decoded_input[1].get('tokenB')}")
    logging.info(f"  Amount A Desired: {w3.from_wei(decoded_input[1].get('amountADesired'), 'ether')}")
    logging.info(f"  Amount B Desired: {w3.from_wei(decoded_input[1].get('amountBDesired'), 'ether')}")

def log_remove_liquidity_details(decoded_input, w3, token_loader):
    params = decoded_input[1]
    logging.info("  Remove Liquidity Details:")
    for key, value in params.items():
        if isinstance(value, (int, float)):
            logging.info(f"    {key}: {w3.from_wei(value, 'ether')}")
        elif isinstance(value, (str, bool)):
            if key.lower() in ['token', 'tokena', 'tokenb']:
                token_info = token_loader.get_token_info(value)
                logging.info(f"    {key}: {token_info['label'] if token_info else value}")
            else:
                logging.info(f"    {key}: {value}")
        elif isinstance(value, list):
            logging.info(f"    {key}: {', '.join(map(str, value))}")
        else:
            logging.info(f"    {key}: {type(value)}")

def log_generic_function_details(decoded_input, w3):
    for key, value in decoded_input[1].items():
        if isinstance(value, (int, float)):
            logging.info(f"  {key}: {w3.from_wei(value, 'ether')}")
        elif isinstance(value, (str, bool)):
            logging.info(f"  {key}: {value}")
        elif isinstance(value, list):
            logging.info(f"  {key}: {', '.join(map(str, value))}")
        else:
            logging.info(f"  {key}: {type(value)}")