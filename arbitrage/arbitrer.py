# Copyright (C) 2013, Maxime Biais <maxime@biais.org>

import public_markets
import observers
import config as config
import time
import logging
import json
from futures import ThreadPoolExecutor, wait

import importlib


class Arbitrer(object):
    def __init__(self):
        self.markets = []
        self.observers = []
        self.updated_markets = {}
        self.init_markets(config.markets)
        self.init_observers(config.observers)
        self.threadpool = ThreadPoolExecutor(max_workers=10)

    def init_markets(self, markets):
        self.market_names = markets
        for market_name in markets:
            try:
#                importlib.import_module('public_markets.' + market_name.lower())
                exec('from public_markets import ' + market_name.lower())
                market = eval( 'public_markets.' + market_name.lower() + '.' +
                              market_name + '()')
                self.markets.append(market)
            except (ImportError, AttributeError) as e:
                print e
                print("%s market name is invalid: Ignored (you should check your config file)" % (market_name))

    def init_observers(self, _observers):
        self.observer_names = _observers
        for observer_name in _observers:
            try:
                exec('import observers.' + observer_name.lower())
                observer = eval('observers.' + observer_name.lower() + '.' +
                                observer_name + '()')
                self.observers.append(observer)
            except (ImportError, AttributeError) as e:
                print("%s observer name is invalid: Ignored (you should check your config file)" % (observer_name))

    def get_profit_for(self, mi, mj, kask, kbid):
        buy_market = self.updated_markets[kask]
        sell_market = self.updated_markets[kbid]

        if buy_market.ask(mi) >= sell_market.bid(mj):
            return 0, 0, 0, 0, 0

        max_amount_buy = buy_market.cum_asize(mi)
        max_amount_sell = sell_market.cum_bsize(mj)
        max_amount = min(max_amount_buy, max_amount_sell, config.max_tx_volume)

        w_buyprice, buy_total = buy_market.wavg_ask(max_amount)
        w_sellprice, sell_total = sell_market.wavg_bid(max_amount)

        profit = sell_total * w_sellprice - buy_total * w_buyprice
        comm = (sell_total * w_sellprice + buy_total * w_buyprice) * (0.2 / 100)
        profit -= comm
        return profit, comm, sell_total, w_buyprice, w_sellprice

    def get_max_depth(self, kask, kbid, max_depth_levels=5):
        """

        :param kask: Market name where we can supposed buy  (ask is lower than nbbo bid)
        :param kbid: Market name where we can supposed sell (bid is higher than nbbo ask)
        :return: (i, j) where i = number of levels of kask market lower than nbbo bid
                  j = number of levels of kbid market lower than nbbo ask
        """
        buy_market = self.updated_markets[kask]    # Buy at this market's ask
        sell_market = self.updated_markets[kbid]   # Sell at this market's bid

        # Find all prices that we can buy at (< ref_price)
        ref_price = sell_market.bid()
        for i, ask in enumerate(buy_market.iter_asks()):
            if ref_price < ask or i >= max_depth_levels:
                break

        # Find all the prices we can sell at (> ref_price)
        ref_price = buy_market.ask()
        for j, bid in enumerate(sell_market.iter_bids()):
            if ref_price > bid or j >= max_depth_levels:
                break

        return i, j


    def arbitrage_depth_opportunity(self, kask, kbid):
        """

        :param kask: Market name to buy at
        :param kbid: Market name to sell at
        :return:
        """
        maxi, maxj = self.get_max_depth(kask, kbid)

        buy_market = self.updated_markets[kask]  # Buy at this market's ask
        sell_market = self.updated_markets[kbid]  # Sell at this market's bid

        max_trade_size = min(buy_market.cum_asize(maxi), sell_market.cum_bsize(maxj),
                             config.max_tx_volume)

        w_buyprice, buy_total = buy_market.wavg_ask(max_trade_size)
        w_sellprice, sell_total = sell_market.wavg_bid(max_trade_size)

        profit = sell_total * w_sellprice - buy_total * w_buyprice
        comm = (sell_total * w_sellprice + buy_total * w_buyprice) * (0.2 / 100)
        profit -= comm

        return profit, comm, max_trade_size, \
               self.updated_markets[kask].ask(), \
               self.updated_markets[kbid].bid(), \
               w_buyprice, w_sellprice


    def arbitrage_opportunity(self, kask, ask, kbid, bid):
        """

        :param kask: Market name to buy at
        :param ask:  buy price
        :param kbid: Market name to sell at
        :param bid: sell price
        :return:
        """
        profit, comm, volume, buyprice, sellprice, weighted_buyprice,\
            weighted_sellprice = self.arbitrage_depth_opportunity(kask, kbid)

        if profit < 0:
            return

        if volume == 0 or buyprice == 0:
            return
        perc2 = (1 - (volume - (profit / buyprice)) / volume) * 100
        for observer in self.observers:
            observer.opportunity(
                profit, comm, volume, buyprice, kask, sellprice, kbid,
                perc2, weighted_buyprice, weighted_sellprice)

    def __get_market_depth(self, market, depths):
        _ = market.update_depth()
        depths[market.name] = market

    def update_depths(self):
        depths = {}
        futures = []
        for market in self.markets:
            futures.append(self.threadpool.submit(self.__get_market_depth,
                                                  market, depths))
        wait(futures, timeout=20)
        return depths

    def tickers(self):
        for market in self.markets:
            logging.verbose("ticker: " + market.name + " - " + str(
                market.get_ticker()))

    def replay_history(self, directory):
        import os
        import json
        import pprint
        files = os.listdir(directory)
        files.sort()
        for f in files:
            depths = json.load(open(directory + '/' + f, 'r'))
            self.updated_markets = {}
            for market in self.market_names:
                if market in depths:
                    self.updated_markets[market] = depths[market]
            self.tick()

    def tick(self):
        for observer in self.observers:
            observer.begin_opportunity_finder(self.updated_markets)

        for kmarket1 in self.updated_markets:
            for kmarket2 in self.updated_markets:
                if kmarket1 == kmarket2:  # same market
                    continue
                market1 = self.updated_markets[kmarket1]
                market2 = self.updated_markets[kmarket2]

                # is market1.ask < market2.bid ?
                if market1.is_valid() and market2.is_valid():
                    if market2.bid() > market1.ask():
                        self.arbitrage_opportunity(kmarket1, market1.ask(),
                                                   kmarket2, market2.bid())

        for observer in self.observers:
            observer.end_opportunity_finder()

        for observer in self.observers:
            observer.end_opportunity_finder()

    def loop(self):
        while True:
            self.updated_markets = self.update_depths()
            self.tickers()
            self.tick()
            time.sleep(config.refresh_rate)
