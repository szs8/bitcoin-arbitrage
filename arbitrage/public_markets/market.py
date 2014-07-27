import time
import config
import logging
import sys
from fiatconverter import FiatConverter
from utils import log_exception


class Market(object):
    def __init__(self, currency):
        self.name = self.__class__.__name__
        self.currency = currency
        self.depth_updated = 0
        self.update_rate = 60
        self.fc = FiatConverter()
        self.fc.update()

    def get_depth(self):
        timediff = time.time() - self.depth_updated
        if timediff > self.update_rate:
            self.ask_update_depth()
        timediff = time.time() - self.depth_updated
        if timediff > config.market_expiration_time:
            logging.warn('Market: %s order book is expired' % self.name)
            self.depth = {'asks': [{'price': 0, 'amount': 0}], 'bids': [
                {'price': 0, 'amount': 0}]}
        return self.depth

    def bid(self, level=0):
        return self.get_depth()['bids'][level]['price']

    def ask(self, level=0):
        return self.get_depth()['asks'][level]['price']

    def bsize(self, level=0):
        return self.get_depth()['bids'][level]['amount']

    def asize(self, level=0):
        return self.get_depth()['asks'][level]['amount']

    def num_bid_levels(self):
        return len(self.get_depth()['bids'])

    def num_ask_levels(self):
        return len(self.get_depth()['asks'])

    def iter_bids(self):
        for i in self.get_depth()['bids']:
            yield i['price']

    def iter_asks(self):
        for i in self.get_depth()['asks']:
            yield i['price']

    def cum_bsize(self, level):
        size = 0
        for idx, i in enumerate(self.get_depth()['bids']):
            size += i['amount']
            if idx >= level:
                break
        return size

    def cum_asize(self, level):
        size = 0
        for idx, i in enumerate(self.get_depth()['asks']):
            size += i['amount']
            if idx >= level:
                break
        return size

    def wavg_bid(self, size):
        n, d = 0.0, 0.0
        bids = self.get_depth()['bids']

        for i in bids:
            price, amount = i['price'], i['amount']
            amount_to_take = min(amount, size - d)
            n += price * amount_to_take
            d += amount_to_take
            if d >= size:
                break

        if d > 0:
            return n / d, d
        else:
            return 0

    def wavg_ask(self, size):
        n, d = 0.0, 0.0
        asks = self.get_depth()['asks']
        for i in asks:
            price, amount = i['price'], i['amount']
            amount_to_take = min(amount, size - d)
            n += price * amount_to_take
            d += amount_to_take
            if d >= size:
                break

        if d > 0:
            return n / d, d
        else:
            return 0

    def is_valid(self):
        """
        :return: True, if the market has valid data (bids, offers)
        """
        depth = self.get_depth()
        return 'bids' in depth and len(depth['bids']) > 0 and 'asks' in depth and len(depth['asks']) > 0

    def convert_to_usd(self):
        if self.currency == "USD":
            return
        for direction in ("asks", "bids"):
            for order in self.depth[direction]:
                order["price"] = self.fc.convert(order["price"], self.currency, "USD")

    def ask_update_depth(self):
        try:
            self.update_depth()
            self.convert_to_usd()
            self.depth_updated = time.time()
        except ValueError as e:
            logging.error("HTTPError, can't update market: %s" % self.name)
            log_exception(logging.DEBUG)
        except Exception as e:
            logging.error("Can't update market: %s - %s" % (self.name, str(e)))
            log_exception(logging.DEBUG)

    def get_ticker(self):
        depth = self.get_depth()
        res = {'ask': 0, 'bid': 0}
        if len(depth['asks']) > 0 and len(depth["bids"]) > 0:
            res = {'ask': depth['asks'][0],
                   'bid': depth['bids'][0]}
        return res

    ## Abstract methods
    def update_depth(self):
        pass

    def buy(self, price, amount):
        pass

    def sell(self, price, amount):
        pass
