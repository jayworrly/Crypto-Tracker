# analysis.py

import logging
from collections import defaultdict
from typing import List, Dict, Any
from web3 import Web3

HIGH_VALUE_THRESHOLD_USD = 10000
TIME_PERIOD_UNITS = {'h': 1/24, 'd': 1, 'w': 7}

class AvalancheTransactionAnalyzer:
    def __init__(self, blockchain_connector, token_loader, router_loader, wallet_loader):
        self.blockchain_connector = blockchain_connector
        self.token_loader = token_loader
        self.router_loader = router_loader
        self.wallet_loader = wallet_loader
        self.logger = logging.getLogger(__name__)

    def analyze_transactions(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not transactions:
            raise ValueError("No transactions provided for analysis.")
        
        self.logger.info(f"Analyzing {len(transactions)} transactions")
        return self.analyze_avalanche_transactions(transactions)

    def analyze_avalanche_transactions(self, transactions):
        analysis_results = {
            "total_transactions": len(transactions),
            "total_avax_value": sum(Web3.from_wei(tx.get('value', 0), 'ether') for tx in transactions),
            "unique_addresses": set(),
            "transaction_types": defaultdict(int),
            "dex_interactions": defaultdict(int),
            "token_transfers": defaultdict(lambda: defaultdict(int)),
            "gas_usage": {"total": 0, "average": 0, "max": 0},
            "high_value_transactions": [],
            "labeled_transactions": defaultdict(list)
        }

        for tx in transactions:
            self.process_transaction(tx, analysis_results)

        self.finalize_analysis(analysis_results)
        return analysis_results

    def process_transaction(self, tx, analysis_results):
        from_address, to_address = tx.get('from', ''), tx.get('to', '')
        analysis_results["unique_addresses"].update([from_address, to_address])
        
        tx_type = self._categorize_transaction(tx)
        analysis_results["transaction_types"][tx_type] += 1
        
        self.check_high_value_transaction(tx, analysis_results)
        self.check_dex_interaction(tx, analysis_results)
        self.check_token_transfer(tx, analysis_results)
        self.analyze_gas_usage(tx, analysis_results)

    def finalize_analysis(self, analysis_results):
        if analysis_results["total_transactions"] > 0:
            analysis_results["gas_usage"]["average"] = analysis_results["gas_usage"]["total"] / analysis_results["total_transactions"]
        analysis_results["unique_addresses"] = len(analysis_results["unique_addresses"])

    def _categorize_transaction(self, transaction: Dict[str, Any]) -> str:
        if transaction.get('to') is None:
            return "contract_creation"
        elif transaction.get('input') and transaction.get('input') != '0x':
            return "contract_interaction"
        else:
            return "transfer"

    def check_high_value_transaction(self, tx, analysis_results):
        if 'exchange_rate' in tx:
            usd_value = float(Web3.from_wei(tx.get('value', 0), 'ether')) * tx['exchange_rate']
            if usd_value >= HIGH_VALUE_THRESHOLD_USD:
                analysis_results["high_value_transactions"].append(tx)

    def check_dex_interaction(self, tx, analysis_results):
        to_address = tx.get('to', '')
        if self._categorize_transaction(tx) == "contract_interaction":
            dex_info = self.router_loader.get_router_info(to_address)
            if dex_info:
                analysis_results["dex_interactions"][dex_info['name']] += 1

    def check_token_transfer(self, tx, analysis_results):
        to_address = tx.get('to', '')
        token_info = self.token_loader.get_token_info(to_address)
        if token_info:
            token_symbol = token_info['details'].get('symbol', 'Unknown')
            analysis_results["token_transfers"][token_symbol]["count"] += 1
            analysis_results["labeled_transactions"][token_info['label']].append(tx)

    def analyze_gas_usage(self, tx, analysis_results):
        gas_used = tx.get('gas', 0)
        analysis_results["gas_usage"]["total"] += gas_used
        analysis_results["gas_usage"]["max"] = max(analysis_results["gas_usage"]["max"], gas_used)

    def get_whale_activity(self, address: str, time_period: str) -> Dict[str, Any]:
        self.logger.info(f"Analyzing whale activity for address {address} over {time_period}")
        try:
            transactions = self.blockchain_connector.get_address_transactions(address, time_period)
            activity_analysis = self.analyze_transactions(transactions)
            activity_analysis["address"] = address
            activity_analysis["time_period"] = time_period
            activity_analysis["transaction_frequency"] = len(transactions) / self._convert_time_period_to_days(time_period)
            return activity_analysis
        except Exception as e:
            self.logger.error(f"Error analyzing whale activity: {str(e)}")
            raise

    def _convert_time_period_to_days(self, time_period: str) -> float:
        try:
            value = float(time_period[:-1])
            unit = time_period[-1]
            if unit not in TIME_PERIOD_UNITS:
                raise ValueError(f"Unsupported time period unit: {unit}")
            return value * TIME_PERIOD_UNITS[unit]
        except (ValueError, IndexError):
            raise ValueError(f"Invalid time period format: {time_period}")