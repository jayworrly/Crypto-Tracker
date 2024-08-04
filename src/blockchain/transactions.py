import logging
from decimal import Decimal
from web3 import Web3

def analyze_transaction(tx, avax_to_usd, threshold_usd):
    """Analyze a transaction and log if it exceeds the threshold in USD."""
    try:
        # Ensure transaction is properly accessed as a dictionary
        if not isinstance(tx, dict):
            tx = dict(tx)

        tx_value_wei = tx['value']
        tx_value_avax = Web3.from_wei(tx_value_wei, 'ether')
        
        # Convert Decimal to float before multiplying
        tx_value_usd = float(tx_value_avax) * avax_to_usd

        if tx_value_usd >= threshold_usd:
            logging.info(f"Large transaction detected: Hash={tx['hash'].hex()}, Value={tx_value_usd:.2f} USD, From={tx['from']}, To={tx['to']}")

    except Exception as e:
        logging.error(f"Error analyzing transaction: {e}")