import logging
from collections import defaultdict
from typing import List, Dict, Any
from utils.token_loader import load_token_addresses

# Constants
HIGH_VALUE_THRESHOLD_USD = 10000
TIME_PERIOD_UNITS = {'h': 1/24, 'd': 1, 'w': 7}

class TransactionAnalyzer:
    def __init__(self, blockchain_connector):
        self.blockchain_connector = blockchain_connector
        self.logger = logging.getLogger(__name__)

    def analyze_transactions(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze a list of transactions and return insights.
        
        Args:
            transactions: List of transaction dictionaries.
        
        Returns:
            Dictionary containing analysis results.
        
        Raises:
            ValueError: If the transactions list is empty.
        """
        if not transactions:
            raise ValueError("No transactions provided for analysis.")
        
        self.logger.info(f"Analyzing {len(transactions)} transactions")
        
        # Load token labels
        token_labels = load_token_addresses()

        analysis_results = {
            "total_transactions": len(transactions),
            "total_value": sum(tx.get('value', 0) for tx in transactions),
            "unique_addresses": set(),
            "transaction_types": defaultdict(int),
            "high_value_transactions": [],
            "labeled_transactions": defaultdict(list)
        }

        for tx in transactions:
            # Count unique addresses
            analysis_results["unique_addresses"].update({tx.get('from', ''), tx.get('to', '')})
            
            # Categorize transaction types
            tx_type = self._categorize_transaction(tx)
            analysis_results["transaction_types"][tx_type] += 1
            
            # Identify high-value transactions
            if 'exchange_rate' in tx:
                usd_value = tx['value'] * tx['exchange_rate']
                if usd_value >= HIGH_VALUE_THRESHOLD_USD:
                    analysis_results["high_value_transactions"].append(tx)
            
            # Label transactions with known tokens
            contract_address = tx.get('contract')
            if contract_address in token_labels:
                token_label = token_labels[contract_address]
                analysis_results["labeled_transactions"][token_label].append(tx)

        analysis_results["unique_addresses"] = len(analysis_results["unique_addresses"])

        self.logger.info("Transaction analysis completed")
        return analysis_results

    def _categorize_transaction(self, transaction: Dict[str, Any]) -> str:
        """
        Categorize a transaction based on its characteristics.
        
        Args:
            transaction: Transaction dictionary.
        
        Returns:
            Category of the transaction.
        """
        if transaction.get('to') is None:
            return "contract_creation"
        elif transaction.get('input') and transaction.get('input') != '0x':
            return "contract_interaction"
        else:
            return "transfer"

    def get_whale_activity(self, address: str, time_period: str) -> Dict[str, Any]:
        """
        Analyze activity for a specific address over a given time period.
        
        Args:
            address: The address to analyze.
            time_period: Time period for analysis (e.g., "24h", "7d", "30d").
        
        Returns:
            Dictionary containing whale activity analysis.
        
        Raises:
            ValueError: If the time period format is invalid.
        """
        self.logger.info(f"Analyzing whale activity for address {address} over {time_period}")
        
        try:
            # Fetch transactions for the given address and time period
            transactions = self.blockchain_connector.get_address_transactions(address, time_period)
            
            # Analyze these transactions
            activity_analysis = self.analyze_transactions(transactions)
            
            # Add whale-specific analysis
            activity_analysis["address"] = address
            activity_analysis["time_period"] = time_period
            activity_analysis["transaction_frequency"] = len(transactions) / self._convert_time_period_to_days(time_period)
            
            return activity_analysis
        except Exception as e:
            self.logger.error(f"Error analyzing whale activity: {str(e)}")
            raise

    def _convert_time_period_to_days(self, time_period: str) -> float:
        """
        Convert a time period string to number of days.
        
        Args:
            time_period: Time period string (e.g., "24h", "7d", "30d").
        
        Returns:
            Number of days.
        
        Raises:
            ValueError: If the time period format is invalid.
        """
        try:
            value = float(time_period[:-1])
            unit = time_period[-1]
            if unit not in TIME_PERIOD_UNITS:
                raise ValueError(f"Unsupported time period unit: {unit}")
            return value * TIME_PERIOD_UNITS[unit]
        except (ValueError, IndexError):
            raise ValueError(f"Invalid time period format: {time_period}")