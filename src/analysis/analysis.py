import logging
from collections import defaultdict
from typing import List, Dict, Any
from web3 import Web3
from utils.token_loader import load_token_addresses

class TransactionAnalyzer:
    def __init__(self, blockchain_connector):
        self.blockchain_connector = blockchain_connector
        self.logger = logging.getLogger(__name__)
        self.token_labels = load_token_addresses()  # Load token labels from files
        self.erc20_transfer_signature = Web3.keccak(text="Transfer(address,address,uint256)").hex()

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
            tx_hash = tx['hash']
            try:
                receipt = self.blockchain_connector.get_transaction_receipt(tx_hash)
                
                # Parse transaction logs for ERC-20 transfers
                for log in receipt.get('logs', []):
                    if log['topics'][0] == self.erc20_transfer_signature:
                        from_address = Web3.to_checksum_address('0x' + log['topics'][1].hex()[26:])
                        to_address = Web3.to_checksum_address('0x' + log['topics'][2].hex()[26:])
                        value = int(log['data'], 16)
                        value_avax = Web3.from_wei(value, 'ether')
                        
                        analysis_results["total_value"] += value_avax
                        analysis_results["unique_addresses"].update([from_address, to_address])
                        
                        # Convert value to USD
                        value_usd = value_avax * float(self.blockchain_connector.avax_to_usd)

                        # Check if the transaction involves a labeled contract
                        if log['address'].lower() in self.token_labels:
                            label = self.token_labels[log['address'].lower()]
                            analysis_results["labeled_transactions"][label].append(tx)
                            self.logger.info(f"Transaction to {label}: Hash={tx['hash'].hex()}, "
                                             f"Value={value_avax:.2f} AVAX, "
                                             f"Value in USD={value_usd:.2f}, "
                                             f"From={from_address}")
                        
                        # Identify high-value transactions
                        if value_usd > self._get_high_value_threshold():
                            analysis_results["high_value_transactions"].append({
                                "hash": tx_hash.hex(),
                                "from": from_address,
                                "to": to_address,
                                "value_usd": value_usd
                            })
            except Exception as e:
                self.logger.error(f"Error processing transaction {tx_hash.hex()}: {str(e)}")
        
        analysis_results["unique_addresses"] = len(analysis_results["unique_addresses"])

        self.logger.info("Transaction analysis completed")
        return analysis_results

    def _categorize_transaction(self, transaction: Dict[str, Any]) -> str:
        if transaction.get('to') is None:
            return "contract_creation"
        elif transaction.get('input') and transaction.get('input') != '0x':
            return "contract_interaction"
        else:
            return "transfer"

    def _get_high_value_threshold(self) -> float:
        return 10000  # Example threshold in USD

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
