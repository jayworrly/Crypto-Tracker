# app/database/database_setup.py

import sqlite3
import logging
import os

def setup_database():
    try:
        # Ensure the database directory exists
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'avalanche_addresses.db'))
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Connect to the SQLite database (or create it if it doesn't exist)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create a table for storing addresses (if not exists)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS addresses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT NOT NULL UNIQUE,
            label TEXT NOT NULL,
            category TEXT NOT NULL
        )
        ''')

        # Create a table for storing transactions (if not exists)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_hash TEXT NOT NULL UNIQUE,
            from_address TEXT,
            to_address TEXT,
            value_avax REAL,
            value_usd REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            type TEXT
        )
        ''')
        
        conn.commit()
        conn.close()
        
        logging.info(f"Database setup completed successfully. Path: {db_path}")
        print(f"Database setup completed successfully. Path: {db_path}")
    except Exception as e:
        logging.error(f"An error occurred during database setup: {e}")
        print(f"An error occurred during database setup: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    setup_database()