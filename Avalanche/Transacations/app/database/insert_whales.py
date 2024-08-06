# app/database/insert_whales.py

import sqlite3
import os
import requests
from web3 import Web3

DATABASE = 'app/database/avalanche_addresses.db'
AVALANCHE_RPC_URL = 'https://api.avax.network/ext/bc/C/rpc'
AVALANCHE_ECO_DIR = 'app/avalanche_eco'
WHALES_FILE = os.path.join(AVALANCHE_ECO_DIR, 'whales.txt')

def connect_db():
    """Connect to the SQLite database."""
    return sqlite3.connect(DATABASE)

def get_wallet_balance(web3, address):
    """Fetch the AVAX balance of a given wallet address."""
    try:
        balance_wei = web3.eth.get_balance(address)
        balance_avax = web3.from_wei(balance_wei, 'ether')
        return float(balance_avax)  # Ensure balance is a float
    except Exception as e:
        print(f"Error fetching balance for {address}: {e}")
        return 0.0

def get_avax_price_in_usd():
    """Fetch the current AVAX price in USD using the CoinGecko API."""
    url = "https://api.coingecko.com/api/v3/simple/price?ids=avalanche-2&vs_currencies=usd"
    try:
        response = requests.get(url)
        data = response.json()
        return float(data['avalanche-2']['usd'])  # Ensure price is a float
    except Exception as e:
        print(f"Error fetching AVAX price: {e}")
        return None

def read_whale_data(file_path):
    """Read whale wallet data from a text file."""
    whales = []
    with open(file_path, 'r') as file:
        for line in file.readlines():
            line = line.strip()
            if line:
                try:
                    # Parse address and label
                    address, label = line.split(',', 1)
                    whales.append((address.strip(), label.strip()))
                except ValueError as e:
                    print(f"Error parsing line: '{line}' - {e}")
    return whales

def insert_whales():
    """Insert whale wallet data into the whales table."""
    conn = connect_db()
    cursor = conn.cursor()

    # Create the whales table with the correct schema if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS whales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        address TEXT NOT NULL UNIQUE,
        label TEXT NOT NULL,
        balance_avax REAL,
        balance_usd REAL
    )
    ''')

    # Initialize Web3 connection
    web3 = Web3(Web3.HTTPProvider(AVALANCHE_RPC_URL))
    if not web3.is_connected():
        print("Failed to connect to the Avalanche network")
        return

    # Get AVAX price in USD
    avax_to_usd = get_avax_price_in_usd()
    if avax_to_usd is None:
        print("Could not fetch AVAX price, exiting.")
        return

    # Read whales from the text file
    whales = read_whale_data(WHALES_FILE)

    # Query balance and insert whale data
    for address, label in whales:
        try:
            # Fetch balance
            balance_avax = get_wallet_balance(web3, Web3.to_checksum_address(address))
            balance_usd = balance_avax * avax_to_usd

            # Insert into the database
            cursor.execute('''
            INSERT OR REPLACE INTO whales (address, label, balance_avax, balance_usd)
            VALUES (?, ?, ?, ?)
            ''', (address.lower(), label, balance_avax, balance_usd))
            print(f"Inserted whale wallet: {address}, {label}, Balance: {balance_avax:.2f} AVAX, ${balance_usd:.2f} USD")
        except sqlite3.IntegrityError:
            print(f"Wallet {address} already exists in the table.")

    conn.commit()
    conn.close()
    print("Whale wallets inserted successfully.")

if __name__ == "__main__":
    insert_whales()


