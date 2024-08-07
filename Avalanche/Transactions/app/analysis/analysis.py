import logging
from collections import defaultdict
from typing import List, Dict, Any
from web3 import Web3
from utils.token_loader import load_token_addresses

# Constants
HIGH_VALUE_THRESHOLD_USD = 10000
TIME_PERIOD_UNITS = {'h': 1/24, 'd': 1, 'w': 7}

class AvalancheTransactionAnalyzer:
    def __init__(self, blockchain_connector, token_loader):
        self.blockchain_connector = blockchain_connector
        self.token_loader = token_loader
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

        return self.analyze_avalanche_transactions(transactions, token_labels)

    def analyze_avalanche_transactions(self, transactions, token_labels):
        analysis_results = {
            "total_transactions": len(transactions),
            "total_avax_value": sum(Web3.from_wei(tx.get('value', 0), 'ether') for tx in transactions),
            "unique_addresses": set(),
            "transaction_types": defaultdict(int),
            "dex_interactions": defaultdict(int),
            "token_transfers": defaultdict(lambda: defaultdict(int)),
            "gas_usage": {
                "total": 0,
                "average": 0,
                "max": 0
            },
            "high_value_transactions": [],
            "labeled_transactions": defaultdict(list)
        }

        for tx in transactions:
            from_address = tx.get('from', '')
            to_address = tx.get('to', '')
            analysis_results["unique_addresses"].update([from_address, to_address])
            
            # Categorize transaction types
            tx_type = self._categorize_transaction(tx)
            analysis_results["transaction_types"][tx_type] += 1
            
            # Identify high-value transactions
            if 'exchange_rate' in tx:
                usd_value = float(Web3.from_wei(tx.get('value', 0), 'ether')) * tx['exchange_rate']
                if usd_value >= HIGH_VALUE_THRESHOLD_USD:
                    analysis_results["high_value_transactions"].append(tx)
            
            if tx_type == "contract_interaction":
                dex_name = self.identify_dex(to_address)
                if dex_name:
                    analysis_results["dex_interactions"][dex_name] += 1
            
            token_info = self.token_loader.get_token_info(to_address)
            if token_info:
                token_symbol = token_info['details'].get('symbol', 'Unknown')
                analysis_results["token_transfers"][token_symbol]["count"] += 1
                # You might want to decode the input to get the transfer amount
            
            # Label transactions with known tokens
            contract_address = tx.get('to', '')  # Changed from 'contract' to 'to'
            if contract_address in token_labels:
                token_label = token_labels[contract_address]
                analysis_results["labeled_transactions"][token_label].append(tx)

            # Gas usage analysis
            gas_used = tx.get('gas', 0)
            analysis_results["gas_usage"]["total"] += gas_used
            analysis_results["gas_usage"]["max"] = max(analysis_results["gas_usage"]["max"], gas_used)

        # Calculate average gas usage
        if analysis_results["total_transactions"] > 0:
            analysis_results["gas_usage"]["average"] = analysis_results["gas_usage"]["total"] / analysis_results["total_transactions"]

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

    def identify_dex(self, address):
        # This would be a mapping of known DEX addresses to their names
        dex_addresses = {
            "0x60aE616a2155Ee3d9A68541Ba4544862310933d4": "Trader Joe",
            "0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106": "Pangolin",
            # Add more DEX addresses here
        }
        return dex_addresses.get(address, None)