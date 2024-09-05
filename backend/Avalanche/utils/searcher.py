import asyncio
import aiohttp
import json
from pathlib import Path
from web3 import Web3
from web3.middleware import geth_poa_middleware

AVALANCHE_TOKEN_LIST_URL = "https://tokens.coingecko.com/avalanche/all.json"
DEXSCREENER_URL = "https://api.dexscreener.com/latest/dex/tokens"
AVALANCHE_RPC_URL = "https://api.avax.network/ext/bc/C/rpc"
DATABASE_DIR = Path("database")
TOKEN_FILE = DATABASE_DIR / "coins.txt"

# Initialize Web3 connection
w3 = Web3(Web3.HTTPProvider(AVALANCHE_RPC_URL))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

# ERC20 ABI for token detection
ERC20_ABI = json.loads('[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}]')

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

async def fetch_new_tokens(start_block, end_block):
    new_tokens = []
    for block_number in range(start_block, end_block + 1):
        block = w3.eth.get_block(block_number, full_transactions=True)
        for tx in block.transactions:
            if tx['to'] is None:  # Contract creation transaction
                try:
                    contract_address = w3.eth.get_transaction_receipt(tx['hash'])['contractAddress']
                    contract = w3.eth.contract(address=contract_address, abi=ERC20_ABI)
                    
                    # Check if it's an ERC20 token
                    try:
                        name = contract.functions.name().call()
                        symbol = contract.functions.symbol().call()
                        decimals = contract.functions.decimals().call()
                        
                        new_tokens.append({
                            'address': contract_address,
                            'symbol': symbol,
                            'decimals': decimals,
                            'source': 'Blockchain'
                        })
                        print(f"Found new token: {symbol} at {contract_address}")
                    except:
                        pass  # Not an ERC20 token
                except:
                    pass  # Error in contract interaction, skip
    return new_tokens

def merge_token_lists(coingecko_tokens, dexscreener_tokens, blockchain_tokens):
    token_dict = {}

    # Process CoinGecko tokens
    for token in coingecko_tokens:
        address = token['address'].lower()
        if address not in token_dict:
            token_dict[address] = {
                'address': token['address'],
                'symbol': token['symbol'],
                'decimals': token['decimals'],
                'source': 'CoinGecko'
            }

    # Process DEXScreener tokens
    for pair in dexscreener_tokens:
        token = pair.get('baseToken', {})
        address = token.get('address', '').lower()
        if address and address not in token_dict:
            token_dict[address] = {
                'address': token['address'],
                'symbol': token.get('symbol', 'UNKNOWN'),
                'decimals': token.get('decimals', 18),
                'source': 'DEXScreener'
            }
        if address in token_dict:
            token_dict[address]['dexscreener_data'] = {
                'dexId': pair.get('dexId'),
                'pairAddress': pair.get('pairAddress'),
                'liquidity': pair.get('liquidity', {}).get('usd'),
                'volume24h': pair.get('volume', {}).get('h24')
            }

    # Process blockchain tokens
    for token in blockchain_tokens:
        address = token['address'].lower()
        if address not in token_dict:
            token_dict[address] = token

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

def load_existing_tokens():
    existing_tokens = set()
    if TOKEN_FILE.exists():
        with TOKEN_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                address = line.split(',')[0].lower()
                existing_tokens.add(address)
    return existing_tokens

async def main():
    try:
        existing_tokens = load_existing_tokens()
        print(f"Loaded {len(existing_tokens)} existing tokens")

        async with aiohttp.ClientSession() as session:
            print("Fetching Avalanche token lists...")
            coingecko_data = await fetch_token_list(session, AVALANCHE_TOKEN_LIST_URL)

            if coingecko_data:
                coingecko_tokens = [token for token in coingecko_data.get('tokens', coingecko_data) if token['address'].lower() not in existing_tokens]
                print(f"Found {len(coingecko_tokens)} new tokens from CoinGecko")
                
                token_addresses = [token['address'] for token in coingecko_tokens]
                dexscreener_data = await fetch_dexscreener_tokens(session, token_addresses)
            else:
                coingecko_tokens = []
                dexscreener_data = []
                print("No new tokens found from CoinGecko")

        print("API calls completed")

        print(f"DEXScreener data type: {type(dexscreener_data)}")
        print(f"Found {len(dexscreener_data)} token pairs from DEXScreener")

        print("Fetching new tokens from the Avalanche blockchain...")
        latest_block = w3.eth.get_block('latest')['number']
        start_block = latest_block - 1000  # Adjust this range as needed
        blockchain_tokens = await fetch_new_tokens(start_block, latest_block)
        blockchain_tokens = [token for token in blockchain_tokens if token['address'].lower() not in existing_tokens]
        print(f"Found {len(blockchain_tokens)} new tokens from blockchain")

        merged_tokens = merge_token_lists(coingecko_tokens, dexscreener_data, blockchain_tokens)
        print(f"Total new unique tokens after merging: {len(merged_tokens)}")

        if merged_tokens:
            print(f"Appending new Avalanche tokens to {TOKEN_FILE}...")
            with TOKEN_FILE.open("a", encoding="utf-8") as f:
                for token in merged_tokens:
                    line = f"{token['address']},{token['symbol']},{token['decimals']},{token['source']}"
                    if 'dexscreener_data' in token:
                        dex_data = token['dexscreener_data']
                        line += f",{dex_data.get('dexId', 'N/A')},{dex_data.get('pairAddress', 'N/A')},{dex_data.get('liquidity', 'N/A')},{dex_data.get('volume24h', 'N/A')}"
                    f.write(line + "\n")
            print("New Avalanche tokens appended successfully!")

            print("\nSample of new tokens added:")
            for token in merged_tokens[:5]:  # Print first 5 new tokens
                print(f"{token['address']},{token['symbol']},{token['decimals']},{token['source']}")
        else:
            print("No new tokens to add. All tokens are already in the file.")

    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())