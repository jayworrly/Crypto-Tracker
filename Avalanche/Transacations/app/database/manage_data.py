# app/database/manage_data.py

import sqlite3
import os
import logging

DATABASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database', 'avalanche_addresses.db'))

def connect_db():
    """Connect to the SQLite database."""
    try:
        os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
        conn = sqlite3.connect(DATABASE)
        logging.info(f"Connected to database: {DATABASE}")
        return conn
    except sqlite3.Error as e:
        logging.error(f"Error connecting to database: {e}")
        return None
    
def load_addresses(category):
    """Load addresses for a specific category."""
    conn = connect_db()
    if not conn:
        return {}
    cursor = conn.cursor()
    cursor.execute("SELECT address, label FROM addresses WHERE category = ?", (category,))
    results = cursor.fetchall()
    conn.close()
    return {address.lower(): label for address, label in results}

def add_address(address, label, category):
    """Add a new address to the database."""
    conn = connect_db()
    if not conn:
        return
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO addresses (address, label, category) VALUES (?, ?, ?)",
            (address.lower(), label, category)
        )
        conn.commit()
        logging.info(f"Address {address} added successfully.")
    except sqlite3.IntegrityError:
        logging.warning(f"Address {address} already exists.")
    finally:
        conn.close()

def update_address_label(address, new_label):
    """Update the label for an existing address."""
    conn = connect_db()
    if not conn:
        return
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE addresses SET label = ? WHERE address = ?",
        (new_label, address.lower())
    )
    conn.commit()
    conn.close()
    logging.info(f"Address {address} label updated to {new_label}.")

def remove_address(address):
    """Remove an address from the database."""
    conn = connect_db()
    if not conn:
        return
    cursor = conn.cursor()
    cursor.execute("DELETE FROM addresses WHERE address = ?", (address.lower(),))
    conn.commit()
    conn.close()
    logging.info(f"Address {address} removed from database.")

def add_transaction(tx_hash, from_address, to_address, value_avax, value_usd, tx_type):
    """Add a new transaction to the database."""
    conn = connect_db()
    if not conn:
        return
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO transactions 
        (tx_hash, from_address, to_address, value_avax, value_usd, type) 
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (tx_hash, from_address.lower(), to_address.lower(), value_avax, value_usd, tx_type))
        conn.commit()
        logging.info(f"Transaction {tx_hash} added successfully.")
    except sqlite3.IntegrityError:
        logging.warning(f"Transaction {tx_hash} already exists.")
    finally:
        conn.close()

def get_transactions_for_address(address):
    """Get all transactions related to a specific address."""
    conn = connect_db()
    if not conn:
        return []
    cursor = conn.cursor()
    cursor.execute('''
    SELECT tx_hash, from_address, to_address, value_avax, value_usd, timestamp, type
    FROM transactions
    WHERE from_address = ? OR to_address = ?
    ''', (address.lower(), address.lower()))
    transactions = cursor.fetchall()
    conn.close()
    return transactions

def check_database_structure():
    conn = connect_db()
    if not conn:
        logging.error("Failed to connect to the database for structure check.")
        return
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    logging.info(f"Tables in the database: {tables}")
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table[0]})")
        columns = cursor.fetchall()
        logging.info(f"Columns in {table[0]}: {columns}")
    conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    check_database_structure()