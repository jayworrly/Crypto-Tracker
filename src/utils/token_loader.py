import os
import logging

def load_token_addresses(directory='src/avalanche_eco'):
    token_labels = {}
    try:
        for filename in os.listdir(directory):
            if filename.endswith('.txt'):
                filepath = os.path.join(directory, filename)
                with open(filepath, 'r') as file:
                    for line in file:
                        address, label = line.strip().split(',')
                        token_labels[address.strip()] = label.strip()
    except Exception as e:
        logging.error(f"Error loading token addresses: {e}")
    return token_labels