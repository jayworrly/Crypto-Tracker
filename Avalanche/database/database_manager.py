import sqlite3
from datetime import datetime
class DatabaseManager:
    def __init__(self, database_dir):
        self.database_path = f"{database_dir}/transactions.db"
        self.conn = sqlite3.connect(self.database_path)
        self.cursor = self.conn.cursor()
        self._create_table()

    def _create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                tx_hash TEXT PRIMARY KEY,
                sender TEXT,
                recipient TEXT,
                value TEXT,
                timestamp INTEGER,
                avax_value REAL,
                analysis TEXT
            )
        ''')
        self.conn.commit()

    def insert_transaction(self, tx_hash, sender, recipient, value, timestamp, avax_value, analysis):
        self.cursor.execute('''
            INSERT OR REPLACE INTO transactions 
            (tx_hash, sender, recipient, value, timestamp, avax_value, analysis) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (tx_hash, sender, recipient, value, timestamp, avax_value, analysis))
        self.conn.commit()

    def get_transactions_for_date(self, date):
        start_of_day = int(datetime(date.year, date.month, date.day).timestamp())
        end_of_day = start_of_day + 86400  # 86400 seconds in a day
        self.cursor.execute('''
            SELECT * FROM transactions 
            WHERE timestamp >= ? AND timestamp < ?
        ''', (start_of_day, end_of_day))
        return self.cursor.fetchall()

    def get_transactions_between_dates(self, start_date, end_date):
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())
        self.cursor.execute('''
            SELECT * FROM transactions 
            WHERE timestamp >= ? AND timestamp < ?
        ''', (start_timestamp, end_timestamp))
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()
