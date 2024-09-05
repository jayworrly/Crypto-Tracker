import asyncio
from solana.publickey import PublicKey

class WalletMonitor:
    def __init__(self, connector):
        self.connector = connector

    async def monitor_wallet(self, wallet_address):
        while True:
            try:
                pubkey = PublicKey(wallet_address)
                transactions = await self.connector.get_signatures(pubkey)
                
                for tx in transactions:
                    print(f"Wallet {wallet_address} - Transaction: {tx['signature']}")
                
                await asyncio.sleep(10)
            except Exception as e:
                print(f"Error monitoring wallet: {e}")
                await asyncio.sleep(30)

    def monitor_transfers(self):
        # This method would be called by Transaction.py
        # In a real implementation, you'd run this asynchronously
        print("Monitoring wallet transfers...")
