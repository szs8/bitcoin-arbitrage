import json
import sys
import requests
from market import Market


class BitstampUSD(Market):
    def __init__(self):
        super(BitstampUSD, self).__init__("USD")
        self.update_rate = 20

    def update_depth(self):
        url = 'https://www.bitstamp.net/api/order_book/'
        resp = requests.get(url)
        depth = resp.json()
        self.depth = self.format_depth(depth)

    def sort_and_format(self, l, reverse):
        r = []
        for i in l:
            r.append({'price': float(i[0]), 'amount': float(i[1])})
        r.sort(key=lambda x: float(x['price']), reverse=reverse)
        return r

    def format_depth(self, depth):
        bids = self.sort_and_format(depth['bids'], True)
        asks = self.sort_and_format(depth['asks'], False)
        return {'asks': asks, 'bids': bids}

if __name__ == "__main__":
    market = BitstampUSD()
    print(market.get_ticker())
