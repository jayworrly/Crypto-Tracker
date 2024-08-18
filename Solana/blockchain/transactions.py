from .wallet import WalletMonitor
from .Trade_analysis import TradeAnalyzer

class TransactionMonitor:
    def __init__(self):
        self.wallet_monitor = WalletMonitor()
        self.trade_analyzer = TradeAnalyzer()

    def start_monitoring(self):
        print("Starting Solana network monitoring...")
        self.wallet_monitor.monitor_transfers()
        self.trade_analyzer.analyze_trades()