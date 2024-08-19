class Serum:
    def __init__(self, connector):
        self.connector = connector

    def monitor(self):
        print("Monitoring Serum trades...")