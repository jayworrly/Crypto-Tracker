# src/blockchain/transactions.py

import logging
from decimal import Decimal
from web3 import Web3

# Define sets of known addresses
HOT_WALLETS = {
    '0xf89d7b9c864f589bbF53a82105107622B35EaA40': 'Bybit: Hot Wallet',
    '0x9f8c163cBA728e99993ABe7495F06c0A3c8Ac8b9': 'Binance: Hot Wallet',
    '0xb23360CCDd9Ed1b15D45E5d3824Bb409C8D7c460': 'Revolut: Hot Wallet',
    '0x1157A2076b9bB22a85CC2C162f20fAB3898F4101': 'FalconX: Hot Wallet',
    '0xffB3118124cdaEbD9095fA9a479895042018cac2': 'Mexc.com',
    '0x8af8485e1F178be06386CD3877Fde20626e0284F': 'Coinbase: Hot Wallet',
    '0x9Da5812111DCBD65fF9b736874a89751A4F0a2F8': 'Kraken: Hot Wallet',
    # You can add more hot wallet addresses here as needed
}

WHALE_WALLETS = {
    # Add whale wallet addresses here when you have them
    # '0xabcd...': 'Known Whale 1',
    # '0xefgh...': 'Known Whale 2',
}

def analyze_transaction(tx, w3, threshold_usd, avax_to_usd):
    """
    Analyze a single transaction and print relevant information.
    
    :param tx: The transaction dictionary
    :param w3: Web3 instance
    :param threshold_usd: The threshold value in USD for considering a transaction as large
    :param avax_to_usd: The conversion rate from AVAX to USD
    """
    try:
        # Convert Web3 types to Python types
        value = Decimal(w3.from_wei(tx['value'], 'ether'))
        value_usd = value * Decimal(avax_to_usd)
        gas_price = Decimal(w3.from_wei(tx['gasPrice'], 'gwei'))
        gas = Decimal(tx['gas'])
        
        # Calculate gas cost in AVAX
        gas_cost = gas * gas_price / Decimal('1e9')
        
        # Get the transaction receipt for the actual gas used
        tx_receipt = w3.eth.get_transaction_receipt(tx['hash'])
        gas_used = Decimal(tx_receipt['gasUsed'])
        actual_gas_cost = gas_used * gas_price / Decimal('1e9')
        
        print(f"Transaction Analysis:")
        print(f"Hash: {tx['hash'].hex()}")
        print(f"From: {tx['from']} {get_wallet_label(tx['from'].lower())}")
        print(f"To: {tx['to']} {get_wallet_label(tx['to'].lower())}")
        print(f"Value: {value:.4f} AVAX (${value_usd:.2f} USD)")
        print(f"Gas Price: {gas_price:.2f} Gwei")
        print(f"Gas Limit: {gas}")
        print(f"Gas Used: {gas_used}")
        print(f"Actual Gas Cost: {actual_gas_cost:.6f} AVAX")
        print(f"Total Cost: {value + actual_gas_cost:.6f} AVAX")
        
        # Check for transaction significance
        is_large_tx = value_usd >= Decimal(threshold_usd)
        involves_hot_wallet = tx['from'].lower() in HOT_WALLETS or tx['to'].lower() in HOT_WALLETS
        involves_whale = tx['from'].lower() in WHALE_WALLETS or tx['to'].lower() in WHALE_WALLETS
        
        if is_large_tx or involves_hot_wallet or involves_whale:
            logging.info(f"Significant transaction detected:")
            logging.info(f"  Hash: {tx['hash'].hex()}")
            logging.info(f"  From: {tx['from']} {get_wallet_label(tx['from'].lower())}")
            logging.info(f"  To: {tx['to']} {get_wallet_label(tx['to'].lower())}")
            logging.info(f"  Value: {value:.4f} AVAX (${value_usd:.2f} USD)")
            
            if is_large_tx:
                logging.info("  Type: Large Transaction")
            if involves_hot_wallet:
                logging.info("  Type: Involves Hot Wallet")
            if involves_whale:
                logging.info("  Type: Involves Whale Wallet")
        
        # Check if there's any input data (for contract interactions)
        if tx['input'] and tx['input'] != '0x':
            print("This transaction includes contract interaction data.")
        
    except Exception as e:
        logging.error(f"Error analyzing transaction: {str(e)}")

def get_wallet_label(address):
    """Return a label for known wallets, or an empty string if not known."""
    address = address.lower()
    if address in HOT_WALLETS:
        return f"(Hot Wallet: {HOT_WALLETS[address]})"
    elif address in WHALE_WALLETS:
        return f"(Whale Wallet: {WHALE_WALLETS[address]})"
    return ""

# You can add more helper functions here if needed

