from blockchain.connector import SolanaConnector
from blockchain.transactions import TransactionMonitor

def main():
    connector = SolanaConnector()
    monitor = TransactionMonitor(connector)
    monitor.start_monitoring()

if __name__ == "__main__":
    main()