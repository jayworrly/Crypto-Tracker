import sqlite3
from datetime import datetime
import threading
import logging
import json
import os

class DatabaseManager:
    def __init__(self, database_dir):
        self.database_dir = database_dir
        self.connections = {}
        self.cursors = {}
        self.locks = {}
        self.routers = self._load_routers()
        self.coins = self._load_coins()
        self._create_dex_databases()

    def _load_routers(self):
        routers = {}
        router_file = os.path.join(self.database_dir, 'routers.txt')
        try:
            with open(router_file, 'r') as f:
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) == 2:
                        routers[parts[0].lower()] = parts[1]
        except FileNotFoundError:
            logging.error(f"routers.txt not found in {self.database_dir}")
        return routers

    def _load_coins(self):
        coins = {}
        coin_file = os.path.join(self.database_dir, 'coins.txt')
        try:
            with open(coin_file, 'r') as f:
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) == 3:
                        coins[parts[0].lower()] = {'symbol': parts[1], 'name': parts[2]}
        except FileNotFoundError:
            logging.error(f"coins.txt not found in {self.database_dir}")
        return coins

    def _create_dex_databases(self):
        for router_address, dex_name in self.routers.items():
            db_path = os.path.join(self.database_dir, f"{dex_name.lower()}_transactions.db")
            self.connections[router_address] = sqlite3.connect(db_path, check_same_thread=False)
            self.cursors[router_address] = self.connections[router_address].cursor()
            self.locks[router_address] = threading.Lock()
            self._create_tables(router_address)

    def _create_tables(self, router_address):
        with self.locks[router_address]:
            self.cursors[router_address].execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    tx_hash TEXT PRIMARY KEY,
                    sender TEXT,
                    recipient TEXT,
                    value TEXT,
                    timestamp INTEGER,
                    avax_value REAL,
                    gas_cost REAL,
                    input_token_address TEXT,
                    input_token_symbol TEXT,
                    input_token_name TEXT,
                    output_token_address TEXT,
                    output_token_symbol TEXT,
                    output_token_name TEXT,
                    input_amount TEXT,
                    output_amount TEXT,
                    additional_data TEXT
                )
            ''')
            self.connections[router_address].commit()

    def insert_transaction(self, router_address, tx_hash, sender, recipient, value, timestamp, avax_value, gas_cost, 
                           input_token_address, output_token_address, input_amount, output_amount, additional_data):
        router_address = router_address.lower()
        if router_address not in self.connections:
            logging.error(f"Unsupported router address: {router_address}")
            return

        input_token = self.coins.get(input_token_address.lower(), {'symbol': 'UNKNOWN', 'name': 'Unknown'})
        output_token = self.coins.get(output_token_address.lower(), {'symbol': 'UNKNOWN', 'name': 'Unknown'})

        try:
            with self.locks[router_address]:
                self.cursors[router_address].execute('''
                    INSERT INTO transactions 
                    (tx_hash, sender, recipient, value, timestamp, avax_value, gas_cost, 
                     input_token_address, input_token_symbol, input_token_name, 
                     output_token_address, output_token_symbol, output_token_name, 
                     input_amount, output_amount, additional_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (tx_hash, sender, recipient, value, timestamp, avax_value, gas_cost, 
                      input_token_address, input_token['symbol'], input_token['name'],
                      output_token_address, output_token['symbol'], output_token['name'],
                      input_amount, output_amount, json.dumps(additional_data)))
                self.connections[router_address].commit()
        except Exception as e:
            logging.error(f"Error inserting transaction for router {router_address}: {str(e)}", exc_info=True)

    def get_transaction(self, router_address, tx_hash):
        router_address = router_address.lower()
        if router_address not in self.connections:
            logging.error(f"Unsupported router address: {router_address}")
            return None

        with self.locks[router_address]:
            self.cursors[router_address].execute('SELECT * FROM transactions WHERE tx_hash = ?', (tx_hash,))
            transaction = self.cursors[router_address].fetchone()
            
            if not transaction:
                return None
            
            transaction_dict = dict(zip([column[0] for column in self.cursors[router_address].description], transaction))
            transaction_dict['additional_data'] = json.loads(transaction_dict['additional_data'])
            
            return transaction_dict

    def close(self):
        for router_address, conn in self.connections.items():
            conn.close()
