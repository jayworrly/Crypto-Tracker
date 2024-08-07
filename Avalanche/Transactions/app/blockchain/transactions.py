import logging
import os
import json
import requests
import time
from decimal import Decimal
from web3 import Web3
from web3.exceptions import ContractLogicError
from utils.routers import RouterLoader
from utils.wallets import WalletLoader
from utils.token_loader import EnhancedTokenLoader

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Determine the base directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Correct directory paths
utils_directory = os.path.join(current_dir, 'utils')
router_abis_dir = os.path.join(current_dir, 'router_abis')
erc_abis_dir = os.path.join(current_dir, 'erc')

# Check directory existence
if not os.path.exists(utils_directory):
    logging.error(f"Utils directory does not exist: {utils_directory}")
if not os.path.exists(router_abis_dir):
    logging.error(f"Router ABIs directory does not exist: {router_abis_dir}")
if not os.path.exists(erc_abis_dir):
    logging.error(f"ERC ABIs directory does not exist: {erc_abis_dir}")

# Initialize RouterLoader with the correct directory
router_loader = RouterLoader(router_abis_dir)
known_routers = router_loader.get_all_routers()

# Initialize WalletLoader with the correct directory
wallet_loader = WalletLoader(utils_directory)
HOT_WALLETS = wallet_loader.get_all_hot_wallets()
WHALE_WALLETS = wallet_loader.get_all_whale_wallets()

# Initialize Web3
w3 = Web3(Web3.HTTPProvider('https://api.avax.network/ext/bc/C/rpc'))

# Initialize EnhancedTokenLoader with the correct directory
token_loader = EnhancedTokenLoader(utils_directory, w3)
token_mappings = token_loader.get_all_tokens()

def load_abi(file_name):
    file_path = os.path.join(erc_abis_dir, file_name)
    try:
        with open(file_path, 'r') as file:
            abi = json.load(file)
        logging.info(f"Loaded ABI file: {file_name}")
        return abi
    except FileNotFoundError:
        logging.error(f"ABI file not found: {file_name}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding ABI file {file_name}: {e}")
        return None

# Load each ABI
erc20_abi = load_abi('erc20_abi.json')
erc721_abi = load_abi('erc721_abi.json')
erc1155_abi = load_abi('erc1155_abi.json')

def get_wallet_label(address, hot_wallets, whale_wallets, token_loader):
    """Return a label for known wallets or tokens, or an empty string if not known."""
    address = address.lower()
    if address in hot_wallets:
        return f"(Hot Wallet: {hot_wallets[address]})"
    elif address in whale_wallets:
        return f"(Whale Wallet: {whale_wallets[address]})"
    elif address in token_loader.get_all_tokens():
        return f"(Token: {token_loader.get_all_tokens()[address]['label']})"
    return ""

def log_transaction_details(tx, value, value_usd, gas_price_navx, gas, gas_used, actual_gas_cost, total_cost, 
                            is_large_tx, involves_hot_wallet, involves_whale, involves_router, known_routers, hot_wallets, whale_wallets, token_loader, decoded_input):
    """Log details of a significant transaction."""
    from_label = get_wallet_label(tx['from'].lower(), hot_wallets, whale_wallets, token_loader)
    to_label = get_wallet_label(tx['to'].lower(), hot_wallets, whale_wallets, token_loader)
    
    logging.info("\n====================================")
    logging.info("Significant transaction detected:")
    logging.info(f"  Hash: {tx['hash'].hex()}")
    logging.info(f"  From: {tx['from']} {from_label}")
    logging.info(f"  To: {tx['to']} {to_label}")
    logging.info(f"  Value: {value:.4f} AVAX (${value_usd:.2f} USD)")
    logging.info(f"  Gas Price: {gas_price_navx:.8f} nAVAX")  # Display in nAVAX
    logging.info(f"  Gas Limit: {gas}")
    logging.info(f"  Gas Used: {gas_used}")
    logging.info(f"  Actual Gas Cost: {actual_gas_cost:.6f} AVAX")
    logging.info(f"  Total Cost: {total_cost:.6f} AVAX")

    transaction_types = []
    if is_large_tx:
        transaction_types.append("Large Transaction")
    if involves_hot_wallet:
        transaction_types.append("Involves Hot Wallet")
    if involves_whale:
        transaction_types.append("Involves Whale Wallet")
    if involves_router:
        router_name = known_routers[tx['to'].lower()]['name']
        transaction_types.append(f"Dex: {router_name}")
    
    if transaction_types:
        logging.info("  Type: " + ", ".join(transaction_types))
    
    if decoded_input:
        logging.info("Decoded Input:")
        logging.info(f"  Function: {decoded_input[0]}")
        logging.info(f"  Parameters: {decoded_input[1]}")
        
        if 'swapExactTokensForTokens' in decoded_input[0] or 'swapTokensForExactTokens' in decoded_input[0]:
            swap_details = parse_token_swap(decoded_input)
            logging.info("Token Swap Details:")
            logging.info(f"  Swap From: {swap_details['from_token']}")
            logging.info(f"  Swap To: {swap_details['to_token']}")
            logging.info(f"  Amount In: {swap_details['amount_in']} {swap_details['from_token']}")
            logging.info(f"  Amount Out Min: {swap_details['amount_out_min']} {swap_details['to_token']}")

    logging.info("====================================\n")

def parse_token_swap(decoded_input):
    """Parse the token swap details from the decoded input."""
    swap_details = {
        'from_token': '',
        'to_token': '',
        'amount_in': '',
        'amount_out_min': ''
    }
    function_name, params = decoded_input

    if function_name == 'swapExactTokensForTokens':
        swap_details['from_token'] = params[0]
        swap_details['to_token'] = params[1]
        swap_details['amount_in'] = params[2]
        swap_details['amount_out_min'] = params[3]
    elif function_name == 'swapTokensForExactTokens':
        swap_details['from_token'] = params[0]
        swap_details['to_token'] = params[1]
        swap_details['amount_in'] = params[2]
        swap_details['amount_out_min'] = params[3]

    return swap_details

def fallback_decode(w3, input_data):
    try:
        decoded_input = w3.codec.decode_function_input(input_data)
        return decoded_input
    except Exception:
        return ("unknown", {})

def decode_and_process_input(w3, tx, token_loader):
    """Decode and process the input data of a transaction."""
    try:
        erc20_abi = token_loader.get_token_info(tx['to']).get('details').get('abi')
        contract = w3.eth.contract(address=tx['to'], abi=erc20_abi)
        decoded_input = contract.decode_function_input(tx['input'])
        return decoded_input
    except Exception:
        function_name, decoded_data = fallback_decode(w3, tx['input'])
        if function_name != "unknown":
            return (function_name, decoded_data)
        else:
            return None

def analyze_transaction(tx, w3, threshold_usd, avax_to_usd, token_loader, router_loader, wallet_loader, known_routers):
    """Analyze a single transaction and print relevant information."""
    try:
        # Retrieve the transaction receipt
        tx_receipt = w3.eth.get_transaction_receipt(tx['hash'])

        # Check the transaction status
        if tx_receipt['status'] == 0:
            logging.info(f"Transaction {tx['hash'].hex()} failed. Skipping analysis.")
            return  # Skip processing this transaction if it failed

        # Calculate the AVAX value and its equivalent USD value
        value = Decimal(w3.from_wei(tx['value'], 'ether'))
        value_usd = value * Decimal(avax_to_usd)

        # Adjust gas price and calculation for nAVAX
        gas_price_navx = Decimal(w3.from_wei(tx['gasPrice'], 'nano'))  # Using 'nano' for nAVAX
        gas = Decimal(tx['gas'])
        gas_used = Decimal(tx_receipt['gasUsed'])
        actual_gas_cost = gas_used * gas_price_navx / Decimal('1e9')  # Convert nAVAX to AVAX

        total_cost = value + actual_gas_cost

        # Determine if the transaction is significant
        is_large_tx = value_usd >= Decimal(threshold_usd)
        involves_hot_wallet = wallet_loader.is_hot_wallet(tx['from']) or wallet_loader.is_hot_wallet(tx['to'])
        involves_whale = wallet_loader.is_whale_wallet(tx['from']) or wallet_loader.is_whale_wallet(tx['to'])
        involves_router = tx['to'].lower() in known_routers

        # Decode the input if the transaction has one
        decoded_input = None
        if tx['input'] and tx['input'] != '0x':
            decoded_input = decode_and_process_input(w3, tx, token_loader)

        # Log the transaction if it meets any significance criteria
        if is_large_tx or involves_hot_wallet or involves_whale or involves_router:
            log_transaction_details(
                tx, value, value_usd, gas_price_navx, gas, gas_used, actual_gas_cost, total_cost, 
                is_large_tx, involves_hot_wallet, involves_whale, involves_router, known_routers,
                wallet_loader.get_all_hot_wallets(), wallet_loader.get_all_whale_wallets(), token_loader,
                decoded_input
            )

    except Exception as e:
        logging.error(f"Error analyzing transaction {tx['hash'].hex()}: {str(e)}")
