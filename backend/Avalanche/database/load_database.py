import os
import sys
import argparse
from datetime import datetime, timedelta
from database_manager import DatabaseManager

def display_transactions(transactions):
    for tx in transactions:
        print(f"Transaction Hash: {tx[0]}")
        print(f"Sender: {tx[1]}")
        print(f"Recipient: {tx[2]}")
        print(f"Value: {tx[3]} AVAX")
        print(f"Timestamp: {datetime.fromtimestamp(tx[4])}")
        print(f"AVAX Value: {tx[5]}")
        print(f"Analysis: {tx[6]}")
        print("-" * 50)

def load_database(args):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    database_dir = os.path.join(current_dir, 'database')
    db_manager = DatabaseManager(database_dir)

    try:
        if args.date:
            date = datetime.strptime(args.date, "%Y-%m-%d")
        else:
            date = datetime.utcnow()

        if args.last_n_days:
            start_date = date - timedelta(days=args.last_n_days)
            end_date = date + timedelta(days=1)  # Include the full last day
            transactions = db_manager.get_transactions_between_dates(start_date, end_date)
        else:
            transactions = db_manager.get_transactions_for_date(date)

        if not transactions:
            print(f"No transactions found for the specified date or range.")
        else:
            print(f"Found {len(transactions)} transactions.")
            display_transactions(transactions)

    except Exception as e:
        print(f"An error occurred while loading the database: {str(e)}")
    finally:
        db_manager.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load and display transactions from transactions.db")
    parser.add_argument("--date", help="Date to load transactions for (YYYY-MM-DD)")
    parser.add_argument("--last-n-days", type=int, help="Load transactions for the last N days")
    args = parser.parse_args()

    load_database(args)
