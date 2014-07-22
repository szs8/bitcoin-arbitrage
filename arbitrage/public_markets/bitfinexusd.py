import requests
import logging
from market import Market


class BitfinexUSD(Market):
    def __init__(self):
        super(BitfinexUSD, self).__init__("USD")
        self.update_rate = 20
        self.depth = {'asks': [{'price': 0, 'amount': 0}], 'bids': [
            {'price': 0, 'amount': 0}]}

    def update_depth(self):
        resp = requests.get('https://api.bitfinex.com/v1/book/btcusd')
        try:
            depth = resp.json()
        except Exception:
            logging.error("%s - Can't parse json: %s" % (self.name, jsonstr))
        self.depth = self.format_depth(depth)

    def sort_and_format(self, l, reverse=False):
        l.sort(key=lambda x: float(x["price"]), reverse=reverse)
        r = []
        for i in l:
            r.append({'price': float(i['price']),
                      'amount': float(i['amount'])})
        return r

    def format_depth(self, depth):
        bids = self.sort_and_format(depth['bids'], True)
        asks = self.sort_and_format(depth['asks'], False)
        return {'asks': asks, 'bids': bids}
