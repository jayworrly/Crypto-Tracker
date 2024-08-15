# query_tokens.py
import os
from solana.publickey import PublicKey
from solana.rpc.api import Client


# Initialize the Solana RPC client for the mainnet
solana_client = Client("https://api.mainnet-beta.solana.com")

# Solana Token Program ID
TOKEN_PROGRAM_ID = PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")

# Directory and file where token contracts will be stored
DATABASE_DIR = "database"
COINS_FILE = os.path.join(DATABASE_DIR, "coins.txt")

# Function to fetch all token accounts on Solana and store them in coins.txt
def get_all_token_accounts():
    try:
        # Fetch all accounts associated with the token program
        response = solana_client.get_program_accounts(TOKEN_PROGRAM_ID)

        # Ensure the database directory exists
        if not os.path.exists(DATABASE_DIR):
            os.makedirs(DATABASE_DIR)

        # Open or create the coins.txt file for writing token addresses
        with open(COINS_FILE, "w") as file:
            if response["result"]:
                token_accounts = response["result"]
                print(f"Total Token Accounts Found: {len(token_accounts)}")
                for account in token_accounts:
                    token_mint_address = account['pubkey']
                    file.write(f"{token_mint_address}\n")
                print(f"All token mint addresses have been written to {COINS_FILE}.")
            else:
                print("No token accounts found.")
    except Exception as e:
        print(f"An error occurred: {e}")
