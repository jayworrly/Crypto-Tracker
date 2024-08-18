from .dex import Jupiter, Raydium, Orca, Serum

class TradeAnalyzer:
    def __init__(self):
        self.jupiter = Jupiter()
        self.raydium = Raydium()
        self.orca = Orca()
        self.serum = Serum()

    def analyze_trades(self):
        # This method would be called by Transaction.py
        print("Analyzing trades across DEXs...")
        self.jupiter.monitor()
        self.raydium.monitor()
        self.orca.monitor()
        self.serum.monitor()