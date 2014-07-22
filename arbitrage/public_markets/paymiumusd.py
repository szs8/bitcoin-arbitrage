import requests
from market import Market


class PaymiumUSD(Market):
    def __init__(self):
        super(PaymiumUSD, self).__init__("USD")
        self.update_rate = 60

    def update_depth(self):
        resp = requests.get('https://paymium.com/api/v1/depth?currency=USD')
        depth = resp.json()
        self.depth = self.format_depth(depth)

    def sort_and_format(self, l, reverse=False):
        l.sort(key=lambda x: float(x['price']), reverse=reverse)
        r = []
        for i in l:
            r.append({'price': float(i[
                     'price']), 'amount': float(i['amount'])})
        return r

    def format_depth(self, depth):
        bids = self.sort_and_format(depth['bids'], True)
        asks = self.sort_and_format(depth['asks'], False)
        return {'asks': asks, 'bids': bids}

if __name__ == "__main__":
    market = PaymiumEUR()
    print(market.get_ticker())
