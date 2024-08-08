import logging
from decimal import Decimal
from web3 import Web3

def analyze_wallet_transfer(tx, w3, avax_to_usd, wallet_loader, token_loader):
    """Analyze and log wallet-to-wallet transfers."""
    value = Decimal(w3.from_wei(tx['value'], 'ether'))
    value_usd = value * Decimal(avax_to_usd)
    
    from_label = get_wallet_label(tx['from'], wallet_loader, token_loader)
    to_label = get_wallet_label(tx['to'], wallet_loader, token_loader)
    
    if from_label or to_label:  # Only log if either the sender or receiver is a known wallet
        logging.info("\n====================================")
        logging.info("Wallet Transfer Detected:")
        logging.info(f"  Hash: {tx['hash'].hex()}")
        logging.info(f"  From: {tx['from']} {from_label}")
        logging.info(f"  To: {tx['to']} {to_label}")
        logging.info(f"  Value: {value:.4f} AVAX (${value_usd:.2f} USD)")
        logging.info("====================================\n")

def get_wallet_label(address, wallet_loader, token_loader):
    """Return a label for known wallets or tokens."""
    address = address.lower()
    if wallet_loader.is_hot_wallet(address):
        return f"(Hot Wallet: {wallet_loader.get_all_hot_wallets()[address]})"
    elif wallet_loader.is_whale_wallet(address):
        return f"(Whale Wallet: {wallet_loader.get_all_whale_wallets()[address]})"
    token_info = token_loader.get_token_info(address)
    if token_info:
        return f"(Token: {token_info['label']})"
    return ""