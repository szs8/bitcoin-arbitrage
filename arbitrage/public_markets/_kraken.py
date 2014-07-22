import requests
from market import Market

class Kraken(Market):
    def __init__(self, currency, code):
        super(Kraken, self).__init__(currency)
        self.code = code
        self.update_rate = 30

    def update_depth(self):
        url = 'https://api.kraken.com/0/public/Depth'
        resp = requests.get(url, params={'pair' : self.code})
        depth = resp.json()
        self.depth = self.format_depth(depth)

    def sort_and_format(self, l, reverse=False):
        l.sort(key=lambda x: float(x[0]), reverse=reverse)
        r = []
        for i in l:
            r.append({'price': float(i[0]), 'amount': float(i[1])})
        return r

    def format_depth(self, depth):
        bids = self.sort_and_format(depth['result'][self.code]['bids'], True)
        asks = self.sort_and_format(depth['result'][self.code]['asks'], False)
        return {'asks': asks, 'bids': bids}
