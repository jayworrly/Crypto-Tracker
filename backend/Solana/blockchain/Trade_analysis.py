from .dex.Jupiter import JupiterClient
from .dex.Raydium import Raydium
from .dex.Orca import Orca
from .dex.Serum import Serum
from blockchain import connector
import asyncio

class TradeAnalyzer:
    def __init__(self, connector, token_loader, token_file_path):
        self.jupiter = JupiterClient(connector, token_loader, token_file_path)
        self.raydium = Raydium(connector)
        self.orca = Orca(connector)
        self.serum = Serum(connector)

    async def analyze_trades(self):
        while True:
            # Analyze Jupiter trades
            await self.jupiter.monitor()

            # Analyze Raydium trades
            await self.raydium.monitor()  # Ensure this is called asynchronously

            # Analyze Orca trades
            await self.orca.monitor()  # Ensure this is called asynchronously

            # Analyze Serum trades
            await self.serum.monitor()  # Ensure this is called asynchronously

            # Wait for 15 seconds before checking again
            await asyncio.sleep(15)