import asyncio
import aiohttp
import json
from pathlib import Path

AVALANCHE_TOKEN_LIST_URL = "https://tokens.coingecko.com/avalanche/all.json"
DEXSCREENER_URL = "https://api.dexscreener.com/latest/dex/tokens"
DATABASE_DIR = Path("database")
TOKEN_FILE = DATABASE_DIR / "coins.txt"

async def fetch_token_list(session, url, retries=3):
    for attempt in range(retries):
        try:
            print(f"Fetching data from {url} (Attempt {attempt + 1}/{retries})")
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"Successfully fetched data from {url}")
                    return data
                else:
                    print(f"Failed to fetch data from {url}: HTTP {response.status}")
        except Exception as e:
            print(f"Error fetching data from {url}: {str(e)}")
        
        if attempt < retries - 1:
            wait_time = 2 ** attempt  # Exponential backoff
            print(f"Retrying in {wait_time} seconds...")
            await asyncio.sleep(wait_time)
    
    return None

async def fetch_dexscreener_tokens(session, token_addresses):
    all_pairs = []
    batch_size = 30
    for i in range(0, len(token_addresses), batch_size):
        batch = token_addresses[i:i+batch_size]
        url = f"{DEXSCREENER_URL}/{','.join(batch)}"
        data = await fetch_token_list(session, url)
        if data and 'pairs' in data:
            all_pairs.extend(data['pairs'])
        await asyncio.sleep(1)  # Rate limiting
    return all_pairs

def merge_token_lists(coingecko_tokens, dexscreener_tokens):
    token_dict = {}

    for token in coingecko_tokens:
        address = token['address'].lower()
        token_dict[address] = {
            'address': token['address'],
            'symbol': token['symbol'],
            'decimals': token['decimals'],
            'source': 'CoinGecko'
        }

    for pair in dexscreener_tokens:
        token = pair.get('baseToken', {})
        address = token.get('address', '').lower()
        if address:
            if address not in token_dict:
                token_dict[address] = {
                    'address': token['address'],
                    'symbol': token.get('symbol', 'UNKNOWN'),
                    'decimals': token.get('decimals', 18),
                    'source': 'DEXScreener'
                }
            else:
                token_dict[address]['dexscreener_data'] = {
                    'dexId': pair.get('dexId'),
                    'pairAddress': pair.get('pairAddress'),
                    'liquidity': pair.get('liquidity', {}).get('usd'),
                    'volume24h': pair.get('volume', {}).get('h24')
                }

    return list(token_dict.values())

def save_tokens(tokens):
    DATABASE_DIR.mkdir(exist_ok=True)
    with TOKEN_FILE.open("w", encoding="utf-8") as f:
        for token in tokens:
            line = f"{token['address']},{token['symbol']},{token['decimals']},{token['source']}"
            if 'dexscreener_data' in token:
                dex_data = token['dexscreener_data']
                line += f",{dex_data.get('dexId', 'N/A')},{dex_data.get('pairAddress', 'N/A')},{dex_data.get('liquidity', 'N/A')},{dex_data.get('volume24h', 'N/A')}"
            f.write(line + "\n")

async def main():
    try:
        async with aiohttp.ClientSession() as session:
            print("Fetching Avalanche token lists...")
            coingecko_data = await fetch_token_list(session, AVALANCHE_TOKEN_LIST_URL)

            if coingecko_data:
                coingecko_tokens = coingecko_data.get('tokens', coingecko_data)
                print(f"Found {len(coingecko_tokens)} tokens from CoinGecko")
                
                token_addresses = [token['address'] for token in coingecko_tokens]
                dexscreener_data = await fetch_dexscreener_tokens(session, token_addresses)
            else:
                coingecko_tokens = []
                dexscreener_data = []
                print("No tokens found from CoinGecko")

        print("API calls completed")

        print(f"DEXScreener data type: {type(dexscreener_data)}")
        print(f"Found {len(dexscreener_data)} token pairs from DEXScreener")

        merged_tokens = merge_token_lists(coingecko_tokens, dexscreener_data)
        print(f"Total unique tokens after merging: {len(merged_tokens)}")

        if merged_tokens:
            print(f"Saving Avalanche tokens to {TOKEN_FILE}...")
            save_tokens(merged_tokens)
            print("Avalanche token list saved successfully!")

            print("\nSample of tokens saved:")
            with TOKEN_FILE.open("r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if i < 5:  # Print first 5 tokens
                        print(line.strip())
                    else:
                        break
        else:
            print("No tokens to save. Please check the API responses.")

    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())