# app/database/update_schema.py

import sqlite3

DATABASE = 'app/database/avalanche_addresses.db'

def update_whales_table():
    """Add missing columns to the whales table."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Add the balance_avax column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE whales ADD COLUMN balance_avax REAL")
    except sqlite3.OperationalError:
        print("Column balance_avax already exists, skipping this step.")

    # Add the balance_usd column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE whales ADD COLUMN balance_usd REAL")
    except sqlite3.OperationalError:
        print("Column balance_usd already exists, skipping this step.")

    conn.commit()
    conn.close()
    print("Schema update completed successfully.")

if __name__ == "__main__":
    update_whales_table()
