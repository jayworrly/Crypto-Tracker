import time
import logging
from collections import defaultdict
from datetime import datetime, timedelta

class AnalysisOverlay:
    def __init__(self):
        self.start_time = datetime.now()
        self.transaction_count = 0
        self.dex_activity = defaultdict(int)
        self.token_activity = defaultdict(int)
        self.whale_activity = defaultdict(int)
        self.total_volume = 0
        self.unique_addresses = set()

    def update(self, transaction_data):
        self.transaction_count += 1
        self.dex_activity[transaction_data.get('dex', 'Unknown')] += 1
        self.token_activity[transaction_data.get('token', 'Unknown')] += 1
        self.whale_activity[transaction_data.get('whale', 'Unknown')] += 1
        self.total_volume += transaction_data.get('volume', 0)
        self.unique_addresses.add(transaction_data.get('address', 'Unknown'))

    def summarize(self):
        current_time = datetime.now()
        elapsed_time = current_time - self.start_time
        
        summary = f"\n{'='*50}\n"
        summary += f"Analysis Summary (Last 30 minutes)\n"
        summary += f"{'='*50}\n"
        summary += f"Time Range: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')} to {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        summary += f"Total Transactions: {self.transaction_count}\n"
        summary += f"Total Volume: {self.total_volume:.2f} AVAX\n"
        summary += f"Unique Addresses: {len(self.unique_addresses)}\n\n"

        summary += "Top 5 DEXes by Activity:\n"
        for dex, count in sorted(self.dex_activity.items(), key=lambda x: x[1], reverse=True)[:5]:
            summary += f"  {dex}: {count} transactions\n"

        summary += "\nTop 5 Tokens by Activity:\n"
        for token, count in sorted(self.token_activity.items(), key=lambda x: x[1], reverse=True)[:5]:
            summary += f"  {token}: {count} transactions\n"

        summary += "\nWhale Activity:\n"
        for whale, count in sorted(self.whale_activity.items(), key=lambda x: x[1], reverse=True)[:5]:
            summary += f"  {whale}: {count} transactions\n"

        summary += f"\nAverage Transactions per Minute: {self.transaction_count / (elapsed_time.total_seconds() / 60):.2f}\n"
        summary += f"{'='*50}\n"

        logging.info(summary)
        self.reset()

    def reset(self):
        self.__init__()

analysis_overlay = AnalysisOverlay()

def update_analysis(transaction_data):
    analysis_overlay.update(transaction_data)
    if datetime.now() - analysis_overlay.start_time >= timedelta(minutes=30):
        analysis_overlay.summarize()

# This function should be called from main.py whenever a new transaction is processed
def process_transaction(transaction_data):
    update_analysis(transaction_data)

def start_analysis():
    logging.info("Starting Avalanche network analysis...")
    analysis_overlay.__init__()  # Reset the analysis overlay
    return analysis_overlay

