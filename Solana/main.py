import asyncio
import os
from blockchain.transactions import TransactionMonitor
from blockchain.connector import SolanaConnector
from utils.token_loader import TokenLoader

async def main():
    connector = SolanaConnector()  # Initialize your connector
    token_loader = TokenLoader()  
    token_file_path = os.path.join("database", "solana_tokens.txt")  # Path to the token file
    monitor = TransactionMonitor(connector, token_loader, token_file_path)
    await monitor.start_monitoring()

if __name__ == "__main__":
    asyncio.run(main())

