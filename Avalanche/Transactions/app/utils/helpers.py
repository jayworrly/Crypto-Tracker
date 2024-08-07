import logging
import requests
from decimal import Decimal
from web3 import Web3

def setup_logging(log_level, log_file='avaxwhale.log'):
    """Set up logging configuration."""
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=getattr(logging, log_level),
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file),  # Log to a file
            logging.StreamHandler()  # Also log to console
        ]
    )

def decode_transaction_input(w3, tx, abi):
    """Decode the transaction input to determine the function call and parameters."""
    try:
        contract = w3.eth.contract(address=tx['to'], abi=abi)
        decoded_input = contract.decode_function_input(tx['input'])
        return decoded_input
    except Exception as e:
        logging.error(f"Error decoding transaction input: {e}")
        return None

def fetch_token_price(token_info):
    """Fetch the price of a token using its pair ID."""
    pair_id = token_info.get('pair_id')
    if not pair_id:
        logging.warning(f"No pair ID available for token {token_info['name']}")
        return None

    url = f"https://api.dexscreener.com/latest/dex/pairs/avalanche/{pair_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        price_usd = data.get('pair', {}).get('priceUsd', None)
        if price_usd:
            return float(price_usd)
        else:
            logging.warning(f"Price not found for pair ID {pair_id}")
            return None
    except requests.RequestException as e:
        logging.error(f"Error fetching token price for pair ID {pair_id}: {e}")
        return None

def get_wallet_label(address, hot_wallets, whale_wallets):
    """Return a label for known wallets, or an empty string if not known."""
    address = address.lower()
    if address in hot_wallets:
        return f"(Hot Wallet: {hot_wallets[address]})"
    elif address in whale_wallets:
        return f"(Whale Wallet: {whale_wallets[address]})"
    return ""

def load_config(config_path):
    """Load configuration from a YAML file."""
    print(f"Attempting to load config from: {config_path}")
    import yaml
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError as e:
        logging.error(f"Configuration file not found: {e}")
        return {}
    except yaml.YAMLError as e:
        logging.error(f"Error parsing configuration file: {e}")
        return {}
    

def calculate_transaction_value(tx, avax_to_usd):
    """Calculate the transaction value in AVAX and USD."""
    value_avax = Decimal(Web3.from_wei(tx['value'], 'ether'))
    value_usd = value_avax * Decimal(avax_to_usd)
    return value_avax, value_usd

# Add more helper functions as needed...

