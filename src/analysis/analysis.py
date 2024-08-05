import logging
from collections import defaultdict
from typing import List, Dict, Any
from web3 import Web3
from decimal import Decimal
from utils.token_loader import load_token_addresses

class TransactionAnalyzer:
    def __init__(self, blockchain_connector):
        self.blockchain_connector = blockchain_connector
        self.logger = logging.getLogger(__name__)
        self.token_labels = load_token_addresses()  # Load token labels from files
        self.erc20_transfer_signature = Web3.keccak(text="Transfer(address,address,uint256)").hex()
        self.high_value_threshold_usd = 10000  # $10,000 threshold for high-value transactions

    def analyze_transactions(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze a list of transactions and return insights.
        
        :param transactions: List of transaction dictionaries
        :return: Dictionary containing analysis results
        """
        self.logger.info(f"Analyzing {len(transactions)} transactions")
        
        analysis_results = {
            "total_transactions": len(transactions),
            "total_value": 0,
            "unique_addresses": set(),
            "transaction_types": defaultdict(int),
            "high_value_transactions": [],
            "labeled_transactions": defaultdict(list)
        }

        for tx in transactions:
            self._analyze_transaction(tx, analysis_results)

        analysis_results["unique_addresses"] = len(analysis_results["unique_addresses"])
        self.logger.info("Transaction analysis completed")
        return analysis_results

    def _analyze_transaction(self, tx: Dict[str, Any], analysis_results: Dict[str, Any]):
        tx_hash = tx['hash']
        try:
            # Analyze native AVAX transfer
            self._analyze_avax_transfer(tx, analysis_results)

            # Analyze ERC-20 transfers
            receipt = self.blockchain_connector.get_transaction_receipt(tx_hash)
            if receipt:
                self._analyze_erc20_transfers(tx, receipt, analysis_results)
            
        except Exception as e:
            self.logger.error(f"Error processing transaction {tx_hash.hex()}: {str(e)}")

    def _analyze_avax_transfer(self, tx: Dict[str, Any], analysis_results: Dict[str, Any]):
        tx_value_wei = tx['value']
        tx_value_avax = Web3.from_wei(tx_value_wei, 'ether')
        tx_value_usd = float(tx_value_avax) * float(self.blockchain_connector.avax_to_usd)

        analysis_results["total_value"] += tx_value_avax
        analysis_results["unique_addresses"].update([tx['from'], tx['to']])
        analysis_results["transaction_types"][self._categorize_transaction(tx)] += 1

        if tx_value_usd >= self.high_value_threshold_usd:
            high_value_tx = {
                "hash": tx['hash'].hex(),
                "from": tx['from'],
                "to": tx['to'],
                "value_avax": float(tx_value_avax),
                "value_usd": tx_value_usd,
                "token": "AVAX"
            }
            analysis_results["high_value_transactions"].append(high_value_tx)
            self.logger.info(f"Large AVAX transaction detected: Hash={tx['hash'].hex()}, "
                             f"Value={tx_value_usd:.2f} USD, From={tx['from']}, To={tx['to']}")

    def _analyze_erc20_transfers(self, tx: Dict[str, Any], receipt: Dict[str, Any], analysis_results: Dict[str, Any]):
        for log in receipt.get('logs', []):
            if log['topics'][0].hex() == self.erc20_transfer_signature:
                token_address = log['address'].lower()
                if token_address in self.token_labels:
                    from_address = Web3.to_checksum_address('0x' + log['topics'][1].hex()[26:])
                    to_address = Web3.to_checksum_address('0x' + log['topics'][2].hex()[26:])
                    
                    try:
                        # Remove '0x' prefix if present and ensure even length
                        data = log['data'][2:] if log['data'].startswith('0x') else log['data']
                        data = data.zfill(len(data) + len(data) % 2)
                        
                        # Use int.from_bytes() for more robust parsing
                        value = int.from_bytes(bytes.fromhex(data), byteorder='big')
                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"Invalid value data in transaction {tx['hash'].hex()}: {log['data']} - Error: {e}")
                        continue

                    value_token = Web3.from_wei(value, 'ether')
                    value_usd = self._get_token_value_usd(token_address, value_token)

                    if value_usd >= self.high_value_threshold_usd:
                        high_value_tx = {
                            "hash": tx['hash'].hex(),
                            "from": from_address,
                            "to": to_address,
                            "value_token": float(value_token),
                            "value_usd": value_usd,
                            "token": self.token_labels[token_address]
                        }
                        analysis_results["high_value_transactions"].append(high_value_tx)
                        analysis_results["labeled_transactions"][self.token_labels[token_address]].append(high_value_tx)
                        self.logger.info(f"Large {self.token_labels[token_address]} transaction detected: "
                                         f"Hash={tx['hash'].hex()}, Value={value_usd:.2f} USD, "
                                         f"From={from_address}, To={to_address}")

    def _categorize_transaction(self, transaction: Dict[str, Any]) -> str:
        if transaction.get('to') is None:
            return "contract_creation"
        elif transaction.get('input') and transaction.get('input') != '0x':
            return "contract_interaction"
        else:
            return "transfer"

    def _get_token_value_usd(self, token_address: str, value_token: Decimal) -> float:
        # This is a placeholder. In a real implementation, you'd fetch the token's price
        # from an oracle or price feed. For now, we'll assume 1:1 with USD for simplicity.
        return float(value_token)

    def get_whale_activity(self, address: str, time_period: str) -> Dict[str, Any]:
        self.logger.info(f"Analyzing whale activity for address {address} over {time_period}")
        
        transactions = self.blockchain_connector.get_address_transactions(address, time_period)
        
        activity_analysis = self.analyze_transactions(transactions)
        
        activity_analysis["address"] = address
        activity_analysis["time_period"] = time_period
        activity_analysis["transaction_frequency"] = len(transactions) / self._convert_time_period_to_days(time_period)
        
        return activity_analysis

    def _convert_time_period_to_days(self, time_period: str) -> float:
        unit = time_period[-1]
        value = float(time_period[:-1])
        if unit == 'h':
            return value / 24
        elif unit == 'd':
            return value
        elif unit == 'w':
            return value * 7
        else:
            raise ValueError(f"Unsupported time period unit: {unit}")