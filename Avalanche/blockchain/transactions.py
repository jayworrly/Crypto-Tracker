import logging
from blockchain.wallet.wallet_transfers import analyze_wallet_transfer
from .trade_analysis import analyze_trade_or_exchange

def analyze_transaction(tx, w3, threshold_usd, avax_to_usd, token_loader, router_loader, wallet_loader, known_routers):
    """Analyze a single transaction and route to appropriate analysis function."""
    try:
        # Check if it's a simple transfer
        if not tx['input'] or tx['input'] == '0x':
            analyze_wallet_transfer(tx, w3, avax_to_usd, wallet_loader, token_loader)
        # Check if it's a trade/exchange
        elif tx['to'].lower() in known_routers:
            analyze_trade_or_exchange(tx, w3, avax_to_usd, router_loader, token_loader)
        # Other contract interactions can be handled here if needed
    except Exception as e:
        logging.error(f"Error analyzing transaction {tx['hash'].hex()}: {str(e)}")