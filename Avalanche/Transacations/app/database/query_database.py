# app/database/query_database.py

import sqlite3

DATABASE = 'app/database/avalanche_addresses.db'

def query_database():
    """Query the SQLite database to display contents."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Execute a query
    cursor.execute('SELECT * FROM addresses LIMIT 10')
    rows = cursor.fetchall()
    
    # Print the results
    print("ID | Address | Label | Category")
    print("---|---------|-------|---------")
    for row in rows:
        print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]}")
    
    conn.close()

if __name__ == "__main__":
    query_database()
