import json
import logging
import asyncio
from solana.publickey import PublicKey
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction, TransactionInstruction
from spl.token.instructions import get_associated_token_address
from blockchain.connector import SolanaConnector

LAMPORTS_PER_SOL = 1_000_000_000

class JupiterClient:
    def __init__(self, client: AsyncClient, public_key: PublicKey, abi_file_path):
        self.client = client
        self.public_key = public_key
        self.abi = self.load_abi(abi_file_path)

    def load_abi(self, abi_file_path):
        """Load the Jupiter ABI from a JSON file with UTF-8 encoding."""
        try:
            with open(abi_file_path, 'r', encoding='utf-8') as abi_file:
                return json.load(abi_file)
        except FileNotFoundError:
            logging.error(f"ABI file not found at {abi_file_path}")
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON: {e}")


    def get_route_instruction(self, route_plan, input_token_account, output_token_account, amount_in, quoted_out_amount):
        """Create a TransactionInstruction using the ABI for a Jupiter route."""
        program_id = PublicKey("JupiterProgramID")  # Replace with actual Jupiter program ID

        # Encoding data based on ABI
        data = {
            "routePlan": route_plan,
            "inAmount": amount_in,
            "quotedOutAmount": quoted_out_amount,
            "slippageBps": 10,  # Example slippage
            "platformFeeBps": 5  # Example platform fee
        }
        
        # Construct the instruction using the ABI
        instruction = TransactionInstruction(
            keys=[
                {"pubkey": input_token_account, "is_signer": False, "is_writable": True},
                {"pubkey": output_token_account, "is_signer": False, "is_writable": True},
                {"pubkey": PublicKey('PlatformFeeAccountPubKey'), "is_signer": False, "is_writable": True},
                # Add other necessary accounts as per the ABI
            ],
            program_id=program_id,
            data=self.encode_transaction_data("route", data)  # Use ABI to encode the data
        )
        return instruction

    def encode_transaction_data(self, method_name, data):
        """Encode the transaction data based on ABI."""
        for instruction in self.abi['instructions']:
            if instruction['name'] == method_name:
                # Use the ABI to encode data as required
                # For simplicity, this should be implemented using the correct encoding
                return json.dumps(data).encode('utf-8')  # This is a placeholder; proper encoding is needed

        raise ValueError(f"Method {method_name} not found in ABI.")

    async def get_route(self, input_mint, output_mint, amount):
        """Find the best route for a swap."""
        logging.info(f"Finding best route from {input_mint} to {output_mint} for {amount / LAMPORTS_PER_SOL:.6f} SOL")
        # Example route (replace with actual API call)
        route = {
            "route_plan": [{"step": "Raydium", "input_mint": input_mint, "output_mint": output_mint}],
            "quoted_out_amount": amount * 0.98  # Assume a 2% slippage
        }
        return route

    async def execute_swap(self, route, input_token_account, output_token_account):
        """Execute a swap on Jupiter using ABI."""
        route_plan = route["route_plan"]
        quoted_out_amount = route["quoted_out_amount"]

        # Build the transaction based on Jupiter ABI
        tx = Transaction()
        instruction = self.get_route_instruction(route_plan, input_token_account, output_token_account, 1_000_000_000, quoted_out_amount)
        tx.add(instruction)
        
        # Sign and send the transaction
        result = await self.client.send_transaction(tx, self.public_key)
        
        logging.info(f"Transaction sent with hash: {result['result']}")
        return result['result']

    async def monitor(self):
        """Monitor swaps and execute trades."""
        input_mint = "So11111111111111111111111111111111111111112"  # SOL
        output_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
        amount = 1_000_000_000  # 1 SOL

        route = await self.get_route(input_mint, output_mint, amount)

        if route:
            input_token_account = await get_associated_token_address(self.public_key, PublicKey(input_mint))
            output_token_account = await get_associated_token_address(self.public_key, PublicKey(output_mint))

            # Execute the swap and log the transaction hash
            tx_hash = await self.execute_swap(route, input_token_account, output_token_account)

            # Fetch and log transaction details
            await self.log_transaction_details(tx_hash, input_mint, output_mint, amount, route['quoted_out_amount'])
        else:
            logging.error("No valid route found for the trade.")

    async def log_transaction_details(self, tx_hash, input_mint, output_mint, input_amount, quoted_out_amount):
        """Log details of the executed transaction in the desired format."""
        tx_details = await self.client.get_transaction(tx_hash)
        block_number = tx_details['result']['slot']
        
        logging.info("\n🔄 Trade/Exchange on Jupiter")
        logging.info("\n📊 Transaction Summary:")
        logging.info(f"🔗 Hash: {tx_hash}")
        logging.info(f"📍 Block: {block_number}")
        
        # Swap details
        logging.info("\n💱 Swap Details:")
        logging.info(f"Input Token: {input_mint}")
        logging.info(f"Input Amount: {input_amount / LAMPORTS_PER_SOL:.6f}")
        logging.info(f"Output Token: {output_mint}")
        logging.info(f"Minimum Output Amount: {quoted_out_amount / LAMPORTS_PER_SOL:.6f}")
        logging.info(f"Path: {input_mint} -> {output_mint}")
        logging.info(f"Recipient: {self.public_key}")
        logging.info(f"Deadline: 15 minutes from now")

        # Transaction addresses
        logging.info("\n👤 Addresses:")
        logging.info(f"Sender: {self.public_key}")
        logging.info(f"Router: Jupiter")

        # Transaction cost
        gas_used = tx_details['result']['meta']['fee'] / LAMPORTS_PER_SOL
        logging.info("\n💸 Transaction Cost:")
        logging.info(f"💰 Value: {input_amount / LAMPORTS_PER_SOL:.4f} SOL")
        logging.info(f"⛽ Gas: {gas_used:.6f} SOL")

        logging.info("===================================")


class TradeAnalyzer:
    def __init__(self, connector, token_loader):
        self.jupiter = JupiterClient(connector.client, connector.public_key, 'jupiter.json')  # Specify ABI file here
    
    async def analyze_trades(self):
        while True:
            # Monitor Jupiter DEX trades
            await self.jupiter.monitor()

            # Sleep before checking again
            await asyncio.sleep(15)
