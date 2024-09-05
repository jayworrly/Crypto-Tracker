import logging
from decimal import Decimal
from web3 import Web3
from datetime import datetime

def analyze_wallet_transfer(tx, w3, avax_to_usd, wallet_loader, token_loader):
    """Analyze and log wallet-to-wallet transfers."""
    value = Decimal(w3.from_wei(tx['value'], 'ether'))
    value_usd = value * Decimal(avax_to_usd)
    
    from_label = get_wallet_label(tx['from'], wallet_loader, token_loader)
    to_label = get_wallet_label(tx['to'], wallet_loader, token_loader)
    
    # Check if it's a regular wallet transfer
    is_regular_transfer = from_label == "(Regular Wallet)" and to_label == "(Regular Wallet)"
    
    # Only proceed if it's not a regular transfer, or if it is but the value is above 1000 AVAX
    if not is_regular_transfer or value > 1000:
        gas_price = Decimal(w3.from_wei(tx['gasPrice'], 'gwei'))
        gas_cost_avax = Decimal(gas_price) * Decimal(tx['gas']) / Decimal(1e9)
        gas_cost_usd = gas_cost_avax * Decimal(avax_to_usd)

        block = w3.eth.get_block(tx['blockNumber'])
        timestamp = datetime.utcfromtimestamp(block['timestamp']).strftime('%Y-%m-%d %H:%M:%S UTC')

        logging.info("\n====================================")
        logging.info("💼 Wallet Transfer Detected")
        logging.info("====================================")
        logging.info(f"🔗 Hash: {tx['hash'].hex()}")
        logging.info(f"📤 From: {tx['from']} {from_label}")
        logging.info(f"📥 To: {tx['to']} {to_label}")
        logging.info(f"💰 Value: {value:.6f} AVAX (${value_usd:.2f} USD)")
        logging.info(f"💱 AVAX Price: ${avax_to_usd:.4f} / AVAX")
        logging.info(f"⛽ Gas Fee: {gas_cost_avax:.6f} AVAX (${gas_cost_usd:.2f} USD)")
        logging.info(f"🕒 Timestamp: {timestamp}")
        
        if value == 0:
            log_token_transfers(tx, w3, token_loader)
        
        logging.info("====================================\n")

def get_wallet_label(address, wallet_loader, token_loader):
    """Return a label for known wallets or indicate if it's a regular wallet transfer."""
    address = address.lower()
    if wallet_loader.is_hot_wallet(address):
        return f"(Hot Wallet: {wallet_loader.get_all_hot_wallets()[address]})"
    elif wallet_loader.is_whale_wallet(address):
        return f"(Whale Wallet: {wallet_loader.get_all_whale_wallets()[address]})"
    else:
        return "(Regular Wallet)"

def log_token_transfers(tx, w3, token_loader):
    """Log token transfers within a transaction."""
    tx_receipt = w3.eth.get_transaction_receipt(tx['hash'])
    for log in tx_receipt.logs:
        if len(log['topics']) == 3 and log['topics'][0].hex() == '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef':
            token_address = log['address']
            token_info = token_loader.get_token_info(token_address)
            token_symbol = token_info['label'] if token_info else 'Unknown Token'
            decimals = token_info['details'].get('decimals', 18) if token_info else 18
            amount = Decimal(int(log['data'], 16)) / Decimal(10**decimals)
            from_address = '0x' + log['topics'][1].hex()[-40:]
            to_address = '0x' + log['topics'][2].hex()[-40:]
            
            logging.info(f"  Token Transfer: {amount:.6f} {token_symbol}")
            logging.info(f"    From: {from_address}")
            logging.info(f"    To: {to_address}")

# Example usage (you can remove or comment this out if not needed)
def process_transactions(transactions, w3, avax_to_usd, wallet_loader, token_loader):
    for tx in transactions:
        analyze_wallet_transfer(tx, w3, avax_to_usd, wallet_loader, token_loader)