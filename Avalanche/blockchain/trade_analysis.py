import logging
import sys
import os
from web3 import Web3
from decimal import Decimal
from blockchain.routers.lbrouter import analyze_lb_router_transaction
from blockchain.routers.pangolin_exchange import analyze_pangolin_transaction
from blockchain.routers.pharaoh import analyze_pharaoh_transaction
from blockchain.routers.traderjoe_lbrouterV2 import analyze_traderjoe_v2_transaction
from blockchain.routers.traderjoe import analyze_traderjoe_router_transaction
from blockchain.routers.gmx import analyze_gmx_transaction
from blockchain.routers.uniswap_V3_router import analyze_uniswap_v3_transaction

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

def analyze_trade_or_exchange(tx, w3, avax_to_usd, router_loader, token_loader):
    router_info = router_loader.get_router_info(tx['to'])
    if router_info:
        try:
            abi = router_info.get('abi')
            if not abi:
                logging.warning(f"Missing ABI for router {router_info['name']}: {tx['hash'].hex()}")
                return

            # Calculate transaction value
            value_avax = Web3.from_wei(tx['value'], 'ether')
            value_usd = Decimal(value_avax) * Decimal(avax_to_usd)

            # Filter based on USD threshold
            if value_usd < 0:  # Adjust this threshold as needed
                return
            # Route to the appropriate router-specific analysis function
            if router_info['name'] == 'LBRouter':
                analyze_lb_router_transaction(tx, w3, avax_to_usd, router_loader, token_loader)
            elif router_info['name'] == 'Pangolin Exchange':
                analyze_pangolin_transaction(tx, w3, avax_to_usd, router_loader, token_loader)
            elif router_info['name'] == 'Pharaoh':
                analyze_pharaoh_transaction(tx, w3, avax_to_usd, router_loader, token_loader)
            elif router_info['name'] == 'TraderJoe LBRouterV2':
                analyze_traderjoe_v2_transaction(tx, w3, avax_to_usd, router_loader, token_loader)
            elif router_info['name'] == 'TraderJoe':
                analyze_traderjoe_router_transaction(tx, w3, avax_to_usd, router_loader, token_loader)
            elif router_info['name'] == 'GMX Router' or router_info['name'] == 'GMX Position Router':
                analyze_gmx_transaction(tx, w3, avax_to_usd, router_loader, token_loader)
            elif router_info['name'] == 'Uniswap V3 Router':
                analyze_uniswap_v3_transaction(tx, w3, avax_to_usd, router_loader, token_loader)
            else:
                logging.info(f"Unhandled router: {router_info['name']} for transaction {tx['hash'].hex()}")

        except Exception as e:
            logging.error(f"Error analyzing transaction {tx['hash'].hex()}: {str(e)}")
    else:
        logging.info(f"Unknown router for transaction: {tx['hash'].hex()}, to: {tx['to']}")