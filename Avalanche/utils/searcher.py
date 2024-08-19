import asyncio
import aiohttp
import json
from pathlib import Path

AVALANCHE_TOKEN_LIST_URL = "https://tokens.coingecko.com/avalanche/all.json"
DATABASE_DIR = Path("database")
TOKEN_FILE = DATABASE_DIR / "coins.txt"

async def fetch_token_list():
    async with aiohttp.ClientSession() as session:
        async with session.get(AVALANCHE_TOKEN_LIST_URL) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Failed to fetch token list: HTTP {response.status}")

def save_tokens(tokens):
    DATABASE_DIR.mkdir(exist_ok=True)
    with TOKEN_FILE.open("w", encoding="utf-8") as f:
        for token in tokens:
            # Save the contract address, symbol, and decimals
            f.write(f"{token['address']},{token['symbol']},{token['decimals']}\n")

async def main():
    try:
        print("Fetching Avalanche token list...")
        token_list = await fetch_token_list()
        
        if 'tokens' in token_list:
            tokens = token_list['tokens']
        else:
            tokens = token_list  # Some lists might not have a 'tokens' key
        
        print(f"Found {len(tokens)} Avalanche tokens")
        
        print(f"Saving Avalanche tokens to {TOKEN_FILE}...")
        save_tokens(tokens)
        print("Avalanche token list saved successfully!")
        
        # Print first few tokens as a sample
        print("\nSample of tokens saved:")
        with TOKEN_FILE.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i < 5:  # Print first 5 tokens
                    print(line.strip())
                else:
                    break
        
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Response content:")
        async with aiohttp.ClientSession() as session:
            async with session.get(AVALANCHE_TOKEN_LIST_URL) as response:
                print(await response.text())

if __name__ == "__main__":
    asyncio.run(main())