import os
import logging

def load_token_addresses():
    token_labels = {}
    files = ['defi.txt', 'meme.txt', 'stablecoins.txt']
    
    for file in files:
        with open(os.path.join('data', file), 'r') as f:
            for line in f:
                address, label = line.strip().split(',')
                token_labels[address.lower()] = label
    
    return token_labels

def setup_logging(log_level):
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )