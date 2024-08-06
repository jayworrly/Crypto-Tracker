
import sqlite3

DATABASE = 'app/database/avalanche_addresses.db'

def create_whale_table():
    """Create a table for whale wallets in the SQLite database."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # SQL command to create the whales table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS whales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        address TEXT NOT NULL UNIQUE,
        label TEXT NOT NULL,
        threshold INTEGER DEFAULT 10000,  -- Default threshold value
        notes TEXT
    )
    ''')

    conn.commit()
    conn.close()
    print("Whale table created successfully.")

if __name__ == "__main__":
    create_whale_table()