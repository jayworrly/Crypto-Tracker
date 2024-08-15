# main.py
import database.query_tokens

def main():
    print("Connecting to Solana blockchain and fetching token contracts...")
    query_tokens.get_all_token_accounts()
    print("Process complete. Tokens stored in database/coins.txt.")

if __name__ == "__main__":
    main()
