# routers.py

import os
import json
import logging

class RouterLoader:
    def __init__(self, router_directory):
        self.router_directory = router_directory
        self.routers = {}
        self.load_routers()

    def load_routers(self):
        routers_file = os.path.join(self.router_directory, 'routers.txt')
        if not os.path.exists(routers_file):
            logging.warning(f"Routers file not found: {routers_file}")
            return

        try:
            with open(routers_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        address, name = line.split(',', 1)
                        address = address.lower()
                        self.routers[address] = {
                            'name': name.strip(),
                            'abi': self.load_abi(name.strip())
                        }
            logging.info(f"Loaded {len(self.routers)} routers")
        except Exception as e:
            logging.error(f"Error loading routers: {str(e)}")

    def load_abi(self, router_name):
        abi_filename = f"{router_name.lower().replace(' ', '_').replace(':', '').replace('.', '')}.json"
        abi_file = os.path.join(self.router_directory, abi_filename)
        if not os.path.exists(abi_file):
            logging.warning(f"ABI file not found for router {router_name}: {abi_file}")
            return None

        try:
            with open(abi_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON in ABI file for router {router_name}")
        except Exception as e:
            logging.error(f"Error loading ABI for router {router_name}: {str(e)}")
        return None

    def get_router_info(self, address):
        return self.routers.get(address.lower())

    def get_all_routers(self):
        return self.routers

# Usage example
# router_loader = RouterLoader('/path/to/router_abis')
# router_info = router_loader.get_router_info('0x1234...')