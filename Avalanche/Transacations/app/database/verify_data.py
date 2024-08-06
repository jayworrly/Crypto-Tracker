# app/database/verify_data.py

import sqlite3

DATABASE = 'app/database/avalanche_addresses.db'

def verify_data():
    """Verify data in the SQLite database."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Verify whales table
    print("Verifying whales table:")
    cursor.execute("SELECT * FROM whales")
    rows = cursor.fetchall()
    print(f"Total whale wallets in database: {len(rows)}")
    print("\nID | Address                             | Label          | Threshold | Notes")
    print("---|-------------------------------------|----------------|-----------|------")
    for row in rows:
        print(f"{row[0]:<3}| {row[1]:<37} | {row[2]:<14} | {row[3]:<9} | {row[4]}")

    print("\nVerifying addresses table:")
    # Verify addresses table for CEX hot wallets
    cursor.execute("SELECT * FROM addresses WHERE category = 'cexhotwallet'")
    rows = cursor.fetchall()
    print(f"Total CEX hot wallets in database: {len(rows)}")
    print("\nID | Address                             | Label                       | Category")
    print("---|-------------------------------------|-----------------------------|---------")
    for row in rows:
        print(f"{row[0]:<3}| {row[1]:<37} | {row[2]:<27} | {row[3]}")

    conn.close()

if __name__ == "__main__":
    verify_data()

