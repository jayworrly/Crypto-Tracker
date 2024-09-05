import asyncio
from .wallet import WalletMonitor
from .Trade_analysis import TradeAnalyzer

class TransactionMonitor:
    def __init__(self, connector, token_loader, token_file_path):
        self.connector = connector
        self.wallet_monitor = WalletMonitor(connector)
        self.trade_analyzer = TradeAnalyzer(connector, token_loader, token_file_path)

    async def start_monitoring(self):
        print("Starting Solana network monitoring...")

        # Continuously monitor wallet transfers and trades every 15 seconds
        while True:
            self.wallet_monitor.monitor_transfers()
            await self.trade_analyzer.analyze_trades()

            # Wait for 15 seconds before checking again
            await asyncio.sleep(15)
