import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from blockchain.connector import AvaxConnector

class TestAvaxConnector(unittest.TestCase):

    @patch('blockchain.connector.Web3')
    def setUp(self, mock_web3):
        self.mock_w3 = MagicMock()
        mock_web3.return_value = self.mock_w3
        mock_web3.HTTPProvider.return_value = MagicMock()
        
        # Mock the config file
        self.mock_config = {
            'avalanche': {
                'rpc_url': 'https://mock.avax.network/ext/bc/C/rpc'
            }
        }
        
        with patch('blockchain.connector.open'), \
             patch('yaml.safe_load', return_value=self.mock_config):
            self.connector = AvaxConnector('mock_config.yaml')

    def test_connection(self):
        self.mock_w3.isConnected.return_value = True
        self.assertTrue(self.connector.w3.isConnected())

    def test_get_latest_block(self):
        mock_block = {'number': 12345, 'hash': '0x1234...'}
        self.mock_w3.eth.get_block.return_value = mock_block
        
        result = self.connector.get_latest_block()
        
        self.assertEqual(result, mock_block)
        self.mock_w3.eth.get_block.assert_called_once_with('latest')

    def test_get_transaction(self):
        mock_tx = {'hash': '0xabcd...', 'from': '0x1234...', 'to': '0x5678...'}
        self.mock_w3.eth.get_transaction.return_value = mock_tx
        
        result = self.connector.get_transaction('0xabcd...')
        
        self.assertEqual(result, mock_tx)
        self.mock_w3.eth.get_transaction.assert_called_once_with('0xabcd...')

    def test_get_balance(self):
        mock_balance = 1000000000000000000  # 1 AVAX in Wei
        self.mock_w3.eth.get_balance.return_value = mock_balance
        
        result = self.connector.get_balance('0x1234...')
        
        self.assertEqual(result, mock_balance)
        self.mock_w3.eth.get_balance.assert_called_once_with('0x1234...')

if __name__ == '__main__':
    unittest.main()