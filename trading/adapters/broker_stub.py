class BrokerStub:
    def place_order(self, symbol, qty, side):
        return {'ok': True}
