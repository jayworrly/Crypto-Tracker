import os
import json
import logging
import re

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
                        abi = self.load_abi(name.strip())
                        if abi:
                            self.routers[address] = {
                                'name': name.strip(),
                                'abi': abi
                            }
                            logging.info(f"Loaded ABI for router: {name.strip()} ({address})")
                        else:
                            logging.warning(f"Failed to load ABI for router: {name.strip()} ({address})")
            logging.info(f"Loaded {len(self.routers)} routers")
        except Exception as e:
            logging.error(f"Error loading routers: {str(e)}")

    def load_abi(self, router_name):
        # Create a normalized filename
        normalized_name = re.sub(r'[^a-z0-9]+', '_', router_name.lower())
        
        # List of possible file name formats
        possible_filenames = [
            f"{normalized_name}.json",
            f"{router_name.lower().replace(' ', '_')}.json",
            f"{router_name.replace(' ', '')}.json",
            f"{normalized_name.replace('_', '')}.json"
        ]

        for filename in possible_filenames:
            abi_file = os.path.join(self.router_directory, filename)
            if os.path.exists(abi_file):
                try:
                    with open(abi_file, 'r') as f:
                        return json.load(f)
                except json.JSONDecodeError:
                    logging.error(f"Invalid JSON in ABI file for router {router_name}: {abi_file}")
                except Exception as e:
                    logging.error(f"Error loading ABI for router {router_name} from {abi_file}: {str(e)}")
            else:
                logging.debug(f"ABI file not found: {abi_file}")

        logging.warning(f"No valid ABI file found for router {router_name}")
        return None

    def get_router_info(self, address):
        return self.routers.get(address.lower())

    def get_all_routers(self):
        return self.routers