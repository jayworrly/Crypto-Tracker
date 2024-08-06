import sys
import os

# Add the src directory to the sys.path to ensure imports can be resolved
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from utils.token_loader import load_token_addresses

def test_token_loader():
    token_labels = load_token_addresses()
    if token_labels:
        for address, label in token_labels.items():
            print(f"Address: {address}, Label: {label}")
    else:
        print("No tokens found or error loading tokens.")

if __name__ == "__main__":
    test_token_loader()
