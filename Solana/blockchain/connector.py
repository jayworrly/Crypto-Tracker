from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed

class SolanaConnector:
    def __init__(self, rpc_url="https://api.mainnet-beta.solana.com"):
        self.client = AsyncClient(rpc_url, commitment=Confirmed)

    async def get_balance(self, public_key):
        response = await self.client.get_balance(public_key)
        return response['result']['value'] / 1e9  # Convert lamports to SOL

    async def get_token_accounts(self, owner):
        response = await self.client.get_token_accounts_by_owner(owner)
        return response['result']['value']

    async def get_signatures(self, address, limit=10):
        response = await self.client.get_signatures_for_address(address, limit=limit)
        return response['result']

    async def get_transaction(self, signature):
        return await self.client.get_transaction(signature)

    async def close(self):
        await self.client.close()