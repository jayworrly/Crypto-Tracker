# app/database/fetch_wallets.py

import sqlite3
import requests
from web3 import Web3

# Constants for the database and Avalanche RPC endpoint
DATABASE = 'app/database/avalanche_addresses.db'
AVALANCHE_RPC_URL = 'https://api.avax.network/ext/bc/C/rpc'

def connect_db():
    """Connect to the SQLite database."""
    return sqlite3.connect(DATABASE)

def get_wallet_balance(web3, address):
    """Fetch the AVAX balance of a given wallet address."""
    try:
        balance_wei = web3.eth.get_balance(address)
        balance_avax = web3.from_wei(balance_wei, 'ether')
        return balance_avax
    except Exception as e:
        print(f"Error fetching balance for {address}: {e}")
        return 0.0

def get_avax_price_in_usd():
    """Fetch the current AVAX price in USD using the CoinGecko API."""
    url = "https://api.coingecko.com/api/v3/simple/price?ids=avalanche-2&vs_currencies=usd"
    try:
        response = requests.get(url)
        data = response.json()
        return data['avalanche-2']['usd']
    except Exception as e:
        print(f"Error fetching AVAX price: {e}")
        return None

def fetch_wallet_balances():
    """Fetch and print wallet balances."""
    conn = connect_db()
    cursor = conn.cursor()

    # Initialize Web3 connection
    web3 = Web3(Web3.HTTPProvider(AVALANCHE_RPC_URL))
    if web3.is_connected():
        print("Successfully connected to the Avalanche network")
    else:
        print("Failed to connect to the Avalanche network")
        return

    # Fetch all whale wallets and CEX hot wallets
    cursor.execute("SELECT address, label FROM whales UNION SELECT address, label FROM addresses WHERE category = 'cexhotwallet'")
    wallet_addresses = cursor.fetchall()

    # Fetch AVAX price in USD
    avax_to_usd = get_avax_price_in_usd()
    if avax_to_usd is None:
        print("Could not fetch AVAX price, exiting.")
        return

    # Query balance for each wallet
    print("\nAddress                              | Label                       | Balance (AVAX) | Balance (USD)")
    print("-------------------------------------|-----------------------------|----------------|--------------")

    for address, label in wallet_addresses:
        try:
            # Fetch balance
            balance_avax = get_wallet_balance(web3, Web3.to_checksum_address(address))
            balance_usd = balance_avax * avax_to_usd
            print(f"{address:<37} | {label:<27} | {balance_avax:>14.2f} | {balance_usd:>12.2f}")
        except Exception as e:
            print(f"Error fetching balance for {address}: {e}")

    conn.close()

if __name__ == "__main__":
    fetch_wallet_balances()
