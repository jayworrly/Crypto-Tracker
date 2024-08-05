import logging
from web3 import Web3

def analyze_transaction(tx, avax_to_usd, threshold_usd):
    """Analyze a transaction and return if it exceeds the threshold in USD."""
    try:
        tx_value_wei = tx['value']
        tx_value_avax = Web3.from_wei(tx_value_wei, 'ether')
        tx_value_usd = float(tx_value_avax) * avax_to_usd

        if tx_value_usd >= threshold_usd:
            return {
                "hash": tx['hash'].hex(),
                "from": tx['from'],
                "to": tx['to'],
                "value_avax": float(tx_value_avax),
                "value_usd": tx_value_usd,
                "token": "AVAX"
            }
    except Exception as e:
        logging.error(f"Error analyzing transaction: {e}")
    
    return None