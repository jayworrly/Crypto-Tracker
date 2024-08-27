from web3 import Web3
from web3.exceptions import ContractLogicError
from web3.middleware import ExtraDataToPOAMiddleware
import yaml
import requests

class BlockchainConnector:
    def __init__(self, config_path):
        self.config = self.load_config(config_path)
        self.w3 = self.connect()
        self.avax_to_usd = self.get_avax_price()

    def load_config(self, config_path):
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)

    def connect(self):
        w3 = Web3(Web3.HTTPProvider(self.config['avalanche']['rpc_url']))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        if not w3.is_connected():
            raise ConnectionError("Failed to connect to the Avalanche network")
        return w3

    def get_recent_transactions(self, block_count=5):
        latest_block_number = self.w3.eth.block_number
        transactions = []
        for i in range(block_count):
            block = self.w3.eth.get_block(latest_block_number - i, full_transactions=True)
            transactions.extend(block['transactions'])
        return transactions

    def get_avax_price(self):
        response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=avalanche-2&vs_currencies=usd")
        data = response.json()
        return data['avalanche-2']['usd']

    def get_address_transactions(self, address, time_period):
        days = self._convert_time_period_to_days(time_period)
        blocks = int(days * 24 * 60 * 60 / 2)  # Assuming 2-second block time
        latest_block = self.w3.eth.get_block('latest')
        from_block = max(0, latest_block.number - blocks)
        
        transactions = []
        for i in range(from_block, latest_block.number + 1):
            block = self.w3.eth.get_block(i, full_transactions=True)
            for tx in block.transactions:
                if tx['from'].lower() == address.lower() or (tx['to'] and tx['to'].lower() == address.lower()):
                    transactions.append(tx)
        return transactions

    def _convert_time_period_to_days(self, time_period):
        units = {'h': 1/24, 'd': 1, 'w': 7}
        value = float(time_period[:-1])
        unit = time_period[-1].lower()
        if unit not in units:
            raise ValueError(f"Unsupported time unit: {unit}")
        return value * units[unit]