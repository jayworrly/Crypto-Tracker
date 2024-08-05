# app/database/verify_data.py

import sqlite3

DATABASE = 'app/database/avalanche_addresses.db'

def verify_data():
    """Verify data in the SQLite database."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Fetch all rows to see how many entries are present
    cursor.execute("SELECT COUNT(*) FROM addresses")
    total_count = cursor.fetchone()[0]
    print(f"Total addresses in database: {total_count}")
    
    # Fetch a few rows to inspect
    cursor.execute("SELECT * FROM addresses LIMIT 50")  # Adjust limit as needed
    rows = cursor.fetchall()
    
    # Print the results
    print("\nID | Address                             | Label                       | Category")
    print("---|-------------------------------------|-----------------------------|---------")
    for row in rows:
        print(f"{row[0]:<3}| {row[1]:<37} | {row[2]:<27} | {row[3]}")

    conn.close()

if __name__ == "__main__":
    verify_data()
