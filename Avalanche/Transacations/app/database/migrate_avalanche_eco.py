# app/database/migrate_avalanche_eco.py

import sqlite3
import os

DATABASE = 'app/database/avalanche_addresses.db'
AVALANCHE_ECO_DIR = 'app/avalanche_eco'

def connect_db():
    """Connect to the SQLite database."""
    return sqlite3.connect(DATABASE)

def migrate_data():
    """Migrate data from text files in the avalanche_eco directory to SQLite database."""
    conn = connect_db()
    cursor = conn.cursor()

    # Ensure the addresses table exists
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS addresses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        address TEXT NOT NULL UNIQUE,
        label TEXT NOT NULL,
        category TEXT NOT NULL
    )
    ''')

    # Iterate over all files in the avalanche_eco directory
    for filename in os.listdir(AVALANCHE_ECO_DIR):
        if filename.endswith('.txt'):
            category = filename.split('.')[0]  # Use the filename as the category
            file_path = os.path.join(AVALANCHE_ECO_DIR, filename)
            print(f"Processing file: {file_path}")

            with open(file_path, 'r') as file:
                for line in file.readlines():
                    line = line.strip()
                    if line:
                        try:
                            address, label = line.split(',', 1)
                            address = address.strip().lower()
                            label = label.strip()
                            cursor.execute('''
                            INSERT OR IGNORE INTO addresses (address, label, category)
                            VALUES (?, ?, ?)
                            ''', (address, label, category))
                            print(f"Inserted: {address}, {label}, {category}")
                        except sqlite3.IntegrityError:
                            print(f"Address {address} already exists in the database.")
                        except ValueError:
                            print(f"Failed to parse line: '{line}' in file {filename}")

    conn.commit()
    conn.close()
    print("Data migration completed successfully.")

if __name__ == "__main__":
    migrate_data()
