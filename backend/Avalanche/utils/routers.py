import os
import json
import logging

class RouterLoader:
    def __init__(self, database_dir, router_abis_dir):
        self.database_dir = database_dir
        self.router_abis_dir = router_abis_dir
        self.routers = self._load_routers()

    def _load_routers(self):
        routers = {}
        router_file_path = os.path.join(self.database_dir, 'routers.txt')
        with open(router_file_path, 'r') as f:
            for line in f:
                address, name = line.strip().split(',')
                abi_path = os.path.join(self.router_abis_dir, f"{name.lower().replace(' ', '_')}.json")
                if os.path.exists(abi_path):
                    with open(abi_path, 'r') as abi_file:
                        abi = json.load(abi_file)
                    routers[address.lower()] = {'name': name, 'abi': abi}
                else:
                    print(f"Warning: ABI file not found for {name}")
        return routers

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
