# app/database/manage_data.py

import sqlite3

def connect_db():
    """Connect to the SQLite database."""
    return sqlite3.connect('app/database/avalanche_addresses.db')

def load_addresses(category):
    """Load addresses for a specific category."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT address, label FROM addresses WHERE category = ?", (category,))
    results = cursor.fetchall()
    conn.close()
    return {address.lower(): label for address, label in results}

def add_address(address, label, category):
    """Add a new address to the database."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO addresses (address, label, category) VALUES (?, ?, ?)",
            (address.lower(), label, category)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"Address {address} already exists.")
    finally:
        conn.close()

def update_address_label(address, new_label):
    """Update the label for an existing address."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE addresses SET label = ? WHERE address = ?",
        (new_label, address.lower())
    )
    conn.commit()
    conn.close()

def remove_address(address):
    """Remove an address from the database."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM addresses WHERE address = ?", (address.lower(),))
    conn.commit()
    conn.close()

def get_transactions_for_address(address):
    """Get all transactions related to a specific address."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT tx_hash, from_address, to_address, value, timestamp
    FROM transactions
    WHERE from_address = ? OR to_address = ?
    ''', (address.lower(), address.lower()))
    transactions = cursor.fetchall()
    conn.close()
    return transactions
