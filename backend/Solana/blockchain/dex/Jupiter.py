import json
import logging
import asyncio
from solders.pubkey import Pubkey as PublicKey
from solders import AsyncClient
from blockchain.connector import SolanaConnector

LAMPORTS_PER_SOL = 1_000_000_000
JUPITER_PROGRAM_ID = "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB"  # Jupiter v6 program ID


class JupiterClient:
    def __init__(self, client: AsyncClient, public_key: PublicKey):
        self.client = client
        self.public_key = public_key

    async def get_recent_jupiter_transactions(self, limit=10):
        """Fetch recent Jupiter transactions."""
        signatures = await self.client.get_signatures_for_address(JUPITER_PROGRAM_ID, limit=limit)
        return signatures['result']

    async def analyze_transaction(self, signature):
        """Analyze a Jupiter transaction."""
        tx_details = await self.client.get_transaction(signature)
        if tx_details['result'] is None:
            logging.error(f"Transaction details not found for signature: {signature}")
            return None

        # Extract relevant information from the transaction
        block_number = tx_details['result']['slot']
        fee = tx_details['result']['meta']['fee']
        
        # Analyze transaction logs to extract swap details
        logs = tx_details['result']['meta']['logMessages']
        swap_details = self.extract_swap_details(logs)

        if swap_details:
            return {
                'signature': signature,
                'block_number': block_number,
                'fee': fee,
                **swap_details
            }
        return None

    def extract_swap_details(self, logs):
        """Extract swap details from transaction logs."""
        input_amount = None
        output_amount = None
        input_token = None
        output_token = None

        for log in logs:
            if "Program log: Instruction: Route" in log:
                # This log indicates a Jupiter swap
                pass
            elif "Program log: Input" in log:
                parts = log.split()
                input_amount = float(parts[-2])
                input_token = parts[-1]
            elif "Program log: Output" in log:
                parts = log.split()
                output_amount = float(parts[-2])
                output_token = parts[-1]

        if input_amount and output_amount and input_token and output_token:
            return {
                'input_amount': input_amount,
                'input_token': input_token,
                'output_amount': output_amount,
                'output_token': output_token
            }
        return None

    async def monitor(self):
        """Monitor Jupiter DEX for recent trades."""
        recent_transactions = await self.get_recent_jupiter_transactions()
        
        for tx in recent_transactions:
            trade_info = await self.analyze_transaction(tx['signature'])
            if trade_info:
                self.log_trade_info(trade_info)

    def log_trade_info(self, trade_info):
        """Log the analyzed trade information."""
        logging.info("\n🔄 Trade/Exchange on Jupiter")
        logging.info("\n📊 Transaction Summary:")
        logging.info(f"🔗 Hash: {trade_info['signature']}")
        logging.info(f"📍 Block: {trade_info['block_number']}")
        
        logging.info("\n💱 Swap Details:")
        logging.info(f"Input Token: {trade_info['input_token']}")
        logging.info(f"Input Amount: {trade_info['input_amount']}")
        logging.info(f"Output Token: {trade_info['output_token']}")
        logging.info(f"Output Amount: {trade_info['output_amount']}")
        logging.info(f"Path: {trade_info['input_token']} -> {trade_info['output_token']}")

        logging.info("\n💸 Transaction Cost:")
        logging.info(f"⛽ Gas: {trade_info['fee'] / LAMPORTS_PER_SOL:.6f} SOL")

        logging.info("===================================")

class TradeAnalyzer:
    def __init__(self, connector: SolanaConnector):
        self.jupiter = JupiterClient(connector.client, connector.public_key)
    
    async def analyze_trades(self):
        while True:
            # Monitor Jupiter DEX trades
            await self.jupiter.monitor()

            # Sleep before checking again
            await asyncio.sleep(15)
