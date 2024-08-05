# app/database/database_setup.py

import sqlite3
import logging

def setup_database():
    try:
        # Connect to the SQLite database (or create it if it doesn't exist)
        conn = sqlite3.connect('app/database/avalanche_addresses.db')
        cursor = conn.cursor()
        
        # Create a table for storing addresses
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS addresses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT NOT NULL UNIQUE,
            label TEXT NOT NULL,
            category TEXT NOT NULL
        )
        ''')

        # Create a table for storing transactions
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_hash TEXT NOT NULL UNIQUE,
            from_address TEXT,
            to_address TEXT,
            value REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(from_address) REFERENCES addresses(address),
            FOREIGN KEY(to_address) REFERENCES addresses(address)
        )
        ''')
        
        conn.commit()
        conn.close()
        
        logging.info("Database setup completed successfully.")
        print("Database setup completed successfully.")
    except Exception as e:
        logging.error(f"An error occurred during database setup: {e}")
        print(f"An error occurred during database setup: {e}")

if __name__ == "__main__":
    setup_database()
