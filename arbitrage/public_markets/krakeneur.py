from ._kraken import Kraken

class KrakenEUR(Kraken):
    def __init__(self):
        super(KrakenEUR, self).__init__("EUR", "XXBTZEUR")
