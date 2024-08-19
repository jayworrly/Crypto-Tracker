import asyncio
import aiohttp
import json
from pathlib import Path

SOLANA_TOKEN_LIST_URL = "https://cdn.jsdelivr.net/gh/solana-labs/token-list@main/src/tokens/solana.tokenlist.json"
DATABASE_DIR = Path("database")
TOKEN_FILE = DATABASE_DIR / "solana_tokens.txt"

async def fetch_token_list():
    async with aiohttp.ClientSession() as session:
        async with session.get(SOLANA_TOKEN_LIST_URL) as response:
            return await response.json()

def save_tokens(tokens):
    DATABASE_DIR.mkdir(exist_ok=True)
    with TOKEN_FILE.open("w", encoding="utf-8") as f:
        for token in tokens:
            # Escape any commas in the token name to avoid CSV parsing issues
            escaped_name = token['name'].replace(',', '\\,')
            # The 'address' field in the Solana token list is equivalent to the contract address
            f.write(f"{token['symbol']},{token['address']},{escaped_name},{token['decimals']}\n")

async def main():
    print("Fetching Solana token list...")
    token_list = await fetch_token_list()
    tokens = token_list['tokens']
    print(f"Found {len(tokens)} tokens")
    
    print(f"Saving tokens to {TOKEN_FILE}...")
    save_tokens(tokens)
    print("Token list saved successfully!")

if __name__ == "__main__":
    asyncio.run(main())