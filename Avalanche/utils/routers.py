import os
import json
import logging

class RouterLoader:
    def __init__(self, database_directory, router_directory):
        self.database_directory = database_directory
        self.router_directory = router_directory
        self.routers = {}
        self.load_routers()

    def load_routers(self):
        # Update the path to load routers.txt from the new location inside blockchain/routers
        routers_file = os.path.join(self.database_directory, 'routers.txt')
        logging.debug(f"Attempting to load routers from: {routers_file}")
        
        if not os.path.exists(routers_file):
            logging.error(f"Routers file not found: {routers_file}")
            return

        try:
            with open(routers_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        address, name = line.split(',', 1)
                        address = address.lower()
                        abi = self.load_abi(name.strip())
                        self.routers[address] = {
                            'name': name.strip(),
                            'abi': abi
                        }
            logging.info(f"Loaded {len(self.routers)} routers")
            logging.debug(f"Loaded routers: {', '.join(self.routers.keys())}")
        except Exception as e:
            logging.error(f"Error loading routers: {str(e)}")

    def load_abi(self, router_name):
        # Update the path to load the ABI JSON files from the new location inside blockchain/routers
        abi_file = os.path.join(self.router_directory, f"{router_name.lower().replace(' ', '_')}.json")
        logging.debug(f"Attempting to load ABI from: {abi_file}")
        
        if not os.path.exists(abi_file):
            logging.error(f"ABI file not found for router {router_name}: {abi_file}")
            return None

        try:
            with open(abi_file, 'r') as f:
                abi = json.load(f)
            logging.debug(f"Successfully loaded ABI for {router_name}")
            return abi
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON in ABI file for router {router_name}")
        except Exception as e:
            logging.error(f"Error loading ABI for router {router_name}: {str(e)}")
        return None

    def get_router_info(self, address):
        return self.routers.get(address.lower())

    def get_all_routers(self):
        return self.routers
