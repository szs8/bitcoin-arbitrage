import logging
from .observer import Observer


class Logger(Observer):
    def opportunity(self, profit, comm,  volume, buyprice, kask, sellprice, kbid, perc,
                    weighted_buyprice, weighted_sellprice):
        #logging.info("profit: %f USD with volume: %f BTC - buy at %.4f (%s) sell at %.4f (%s) ~%.2f%%" % (profit, volume, buyprice, kask, sellprice, kbid, perc))

        logging.info("profit: %f USD with volume: %f BTC, comm %f USD - buy at %.4f (%s) sell at %.4f (%s) ~%.2f%%" % (
            profit, volume, comm, weighted_buyprice, kask, weighted_sellprice, kbid, perc))
