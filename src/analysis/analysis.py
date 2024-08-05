# src/analysis/analysis.py

import logging
from collections import defaultdict
from typing import List, Dict, Any

class TransactionAnalyzer:
    def __init__(self, blockchain_connector):
        self.blockchain_connector = blockchain_connector
        self.logger = logging.getLogger(__name__)

    def analyze_transactions(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze a list of transactions and return insights.
        
        :param transactions: List of transaction dictionaries
        :return: Dictionary containing analysis results
        """
        self.logger.info(f"Analyzing {len(transactions)} transactions")
        
        analysis_results = {
            "total_transactions": len(transactions),
            "total_value": sum(tx.get('value', 0) for tx in transactions),
            "unique_addresses": set(),
            "transaction_types": defaultdict(int),
            "high_value_transactions": []
        }

        for tx in transactions:
            # Count unique addresses
            analysis_results["unique_addresses"].add(tx.get('from', ''))
            analysis_results["unique_addresses"].add(tx.get('to', ''))
            
            # Categorize transaction types
            tx_type = self._categorize_transaction(tx)
            analysis_results["transaction_types"][tx_type] += 1
            
            # Identify high-value transactions
            if tx.get('value', 0) > self._get_high_value_threshold():
                analysis_results["high_value_transactions"].append(tx)

        analysis_results["unique_addresses"] = len(analysis_results["unique_addresses"])

        self.logger.info("Transaction analysis completed")
        return analysis_results

    def _categorize_transaction(self, transaction: Dict[str, Any]) -> str:
        """
        Categorize a transaction based on its characteristics.
        
        :param transaction: Transaction dictionary
        :return: Category of the transaction
        """
        # This is a simplified categorization. You may want to expand this
        # based on your specific needs and the structure of your transactions.
        if transaction.get('to') is None:
            return "contract_creation"
        elif transaction.get('input') and transaction.get('input') != '0x':
            return "contract_interaction"
        else:
            return "transfer"

    def _get_high_value_threshold(self) -> float:
        """
        Determine the threshold for high-value transactions.
        
        :return: Threshold value
        """
        # This could be set in configuration, or dynamically calculated
        # based on recent transaction history.
        return 100  # Example: transactions over 100 AVAX are considered high-value

    def get_whale_activity(self, address: str, time_period: str) -> Dict[str, Any]:
        """
        Analyze activity for a specific address over a given time period.
        
        :param address: The address to analyze
        :param time_period: Time period for analysis (e.g., "24h", "7d", "30d")
        :return: Dictionary containing whale activity analysis
        """
        self.logger.info(f"Analyzing whale activity for address {address} over {time_period}")
        
        # Fetch transactions for the given address and time period
        transactions = self.blockchain_connector.get_address_transactions(address, time_period)
        
        # Analyze these transactions
        activity_analysis = self.analyze_transactions(transactions)
        
        # Add whale-specific analysis
        activity_analysis["address"] = address
        activity_analysis["time_period"] = time_period
        activity_analysis["transaction_frequency"] = len(transactions) / self._convert_time_period_to_days(time_period)
        
        return activity_analysis

    def _convert_time_period_to_days(self, time_period: str) -> float:
        """
        Convert a time period string to number of days.
        
        :param time_period: Time period string (e.g., "24h", "7d", "30d")
        :return: Number of days
        """
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
