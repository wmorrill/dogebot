from binance.client import Client
from binance.enums import *
import pprint
from itertools import chain
import time
import operator
from datetime import datetime, timedelta
import csv
import os
import json
import collections

class BinanceBot:
    def __init__(self, api_key, api_secret):
        self.pp = pprint.PrettyPrinter(indent=4)
        self.api_secret = api_secret
        self.api_key = api_key
        self.client = Client(api_key, api_secret)
        self.coins = {}
        self.ETHUSD = 0
        self.test = True
        self.current_holding = 'ETH'
        self.current_holding_qty = 1  # this is in the above
        self.current_holding_value = 1  # this is in ETH
        self.coins_of_interest = ['TRX', 'XRP', 'XVG', 'NEBL', 'ICX', 'BNB', 'ZRX', 'ADA', 'APPC']
        # should get top 10 most traded coins from binance automatically daily
        self.rate_limits = None
        self.what_is_allowed()
        self.coins['ETH'] = Coin(client=self.client, symbol='ETH')
        for coin in self.coins_of_interest:
            self.coins[coin] = Coin(client=self.client, symbol=coin)
            self.coins['ETH'].add_pair(coin)
    
    def go_live(self):
        self.test = False
        print("This shit just got real...")
    
    def what_is_allowed(self):
        api_limits = self.client.get_exchange_info()
        self.rate_limits = api_limits['rateLimits']
        for d in self.rate_limits:
            if 'REQUESTS' in d['rateLimitType']:
                print("Max Requests per %s: %d" % (d['interval'], d['limit']))
            elif 'ORDERS' in d['rateLimitType']:
                print("Max Orders per %s: %d" % (d['interval'], d['limit']))
        # symbol_limits = api_limits['symbols']
        
    def document_transaction(self, data_list, filename="c:\\git\\dogebot\\trade_documentation.csv"):
        write_headers = False
        if not os.path.isfile(filename):
            write_headers = True
        with open(filename, 'a', newline='') as f:
            writer = csv.writer(f)
            if write_headers:
                writer.writerow(['date', 'holding symbol', 'trade pair', 'type', 'quantity', 'price', 'fee', 'value (eth), value (btc), value (usd)'])
            # data_list = ['date', 'holding symbol', 'trade pair', 'type', 'quantity', 'price', 'fee', 'value (eth), 'value (usd)']
            writer.writerow(data_list)
        
    def trade_buy(self, trade_pair, qty, bid_price=None):
        if bid_price is None: # market order
            self.current_order = self.client.order_market_buy(symbol=trade_pair, quantity=qty, newOrderRespType=ORDER_RESP_TYPE_FULL)
        else:
            self.current_order = self.client.order_limit_buy(symbol=trade_pair,
                                                             quantity=qty,
                                                             price=str(float(bid_price)),
                                                             newOrderRespType=ORDER_RESP_TYPE_FULL)
        orderID = self.current_order['orderId']
        
        # let's make sure this works before moving on
        while(self.current_order['status'] not in "FILLED"): 
            print("Waiting for order to fill...", end="\r")
            self.current_order = self.client.get_order(symbol=trade_pair, orderId=orderID)
            time.sleep(1)
        
        order_price = float(self.current_order['price'])
        qty = float(self.current_order['executedQty'])
        if order_price == 0:
            list_of_sales = [(float(x['price']), float(x['qty'])) for x in self.current_order['fills']]
            avg_price = sum([a*b for (a,b) in list_of_sales])/sum([b for (a,b) in list_of_sales])
            order_price = avg_price
        print("BUY!!! %s: qty: %d price: %f"%(trade_pair, qty, order_price))
        self.current_holding = trade_pair[:-3]
        self.current_holding_qty = qty
        print("now holding: %s, qty: %f, value: %f"%(self.current_holding, self.current_holding_qty, self.current_holding_value))
        
        documentation = [datetime.now(), 
                         self.current_holding, 
                         trade_pair, 
                         'BUY', 
                         qty, 
                         order_price, 
                         order_price*qty*0.001, 
                         self.current_holding_value,
                         self.current_holding_value*self.ETHUSD]
        self.document_transaction(documentation)
        
        return order_price
        
    def trade_sell(self, trade_pair, qty, ask_price=None):
        if ask_price is None: # market order
            self.current_order = self.client.order_market_sell(symbol=trade_pair, quantity=qty, newOrderRespType=ORDER_RESP_TYPE_FULL)
        else: # non-market order
            self.current_order = self.client.order_limit_sell(symbol=trade_pair,
                                                              quantity=qty,
                                                              price=str(float(ask_price)),
                                                              newOrderRespType=ORDER_RESP_TYPE_FULL)
        
        qty = float(self.current_order['qty'])
        print("SELL:%s \tPlacing a sell limit - qty: %d price: %f"%(trade_pair, qty, ask_price))
        time.sleep(1)
        # let's see if this settled immediately
        return self.check_order_status(trade_pair)
    
    def get_order_status(self, trade_pair):
        self.current_order = self.client.get_order(symbol=trade_pair, orderId=self.current_order['orderID'])
        if(self.current_order['status'] not in "FILLED"): 
            return False
        else:    
            self.settle_sell(trade_pair)
            return True
        
    def settle_sell(self, trade_pair):
        order_price = float(self.current_order['price'])
        qty = float(self.current_order['executedQty'])
        if order_price == 0:
            list_of_sales = [(float(x['price']), float(x['qty'])) for x in self.current_order['fills']]
            avg_price = sum([a*b for (a,b) in list_of_sales])/sum([b for (a,b) in list_of_sales])
            order_price = avg_price
        self.current_holding = 'ETH'
        self.current_holding_qty = self.curren_order['executedQty']*order_price
        self.current_holding_value = self.current_holding_qty
        print("now holding: %s, qty: %f, value: %f"%(self.current_holding, self.current_holding_qty, self.current_holding_value))
        documentation = [datetime.now(), 
                         self.current_holding, 
                         trade_pair, 
                         'SELL', 
                         qty, 
                         order_price, 
                         order_price*qty*0.001, 
                         self.current_holding_value,
                         self.current_holding_value*self.ETHUSD]
        self.document_transaction(documentation)
        
    def get_balance(self):
        unique_coins = set(list(chain.from_iterable(self.pairs_of_interest)))
        for coin in unique_coins:
            self.balance[coin] = self.client.get_asset_balance(asset=coin)
        print("current Holdings")
        self.pp.pprint(self.balance)
        
    def cancel_order(self, sym):
        result = self.client.cancel_order(sym, self.current_order['orderID'])
        return result
            
    def get_recent_trades(self, symbol='ETHBTC'):
        recent_trades = self.client.get_recent_trades(symbol='ETHBTC')
        # this returns a dictionary 
        # {'lastUpdateID':123456, 
        # 'bids':[[cost, qty, []], [cost, qty, []], ...], 
        # 'asks':[[cost, qty, []], [cost, qty, []], ...]}

        print('Bids (buy):')
        self.pp.pprint(recent_trades['bids'][:10])
        print('Asks (sell):')
        self.pp.pprint(recent_trades['asks'][:10])
        
        
class MarketDepthBot(BinanceBot):
    def __init__(self, api_key, api_secret):
        super().__init__(api_key, api_secret)
    
    
class VolatilityBot(BinanceBot):
    def __init__(self, api_key, api_secret):
        super().__init__(api_key, api_secret)
        self.purchase_values = {}
        self.current_values = {}
        self.deltas = {}
        self.wait_time = 1
        self.trade_fee = 0.001  # 0.1% fee
        self.total_fees = 0
        self.max_trade_value = 1  # ETH
        self.t0 = datetime.now()
        self.minimum_trade_value = 1.1 * self.current_holding_value * (2 * self.trade_fee) # this is in ETH
                
    def threshold(self, min_price_in_eth=None, time_between_trades=None):
        if min_price_in_eth:
            self.minimum_trade_value = min_price_in_eth
        if time_between_trades:
            self.wait_time = time_between_trades
        else:
            print("Minimum Trade Value (ETH): %f"%self.minimum_trade_value)
            print("Wait Time between price lookup (sec):%d"%self.wait_time)
        
    def trade_buy(self, trade_pair, quantity, price=None):
        print("Time: %s\t Value: %f Total Fees: %f"%(datetime.now(), self.current_holding_value, self.total_fees))
        print("Buy: %s x %f @ %s"%(trade_pair, quantity, str(price)))
        if self.test:
            self.current_holding = trade_pair[:-3]
            self.current_holding_qty = quantity
            return True
        return super().trade_buy(trade_pair, quantity, price)
        
        
    def trade_sell(self, trade_pair, quantity, price=None):
        print("Time: %s\t Value: %f Total Fees: %f"%(datetime.now(), self.current_holding_value, self.total_fees))
        print("Sell: %s x %f @ %s"%(trade_pair, quantity, str(price)))
        if self.test:
            self.current_holding = 'ETH'
            self.current_holding_qty = quantity * price
            self.current_holding_value = quantity * price
            return True
        return super().trade_sell(trade_pair, quantity, price)
        
    def update_values(self, coin = "ETH"):
        allowed_pairs = []
        for cc in self.coins:
            current_coin = self.coins[cc]
            for p in current_coin.pairs:
                if p in "USDT":
                    continue
                sym = current_coin.pair(p)
                self.current_values[sym] = current_coin.price(p, self.current_holding_value)
                if sym not in self.purchase_values.keys():
                    #print(sym, self.purchase_values.keys())
                    self.purchase_values[sym] = self.current_values[sym]
                # print(sym, self.current_values[sym], self.purchase_values[sym])
                try:
                    self.deltas[sym] = (self.current_values[sym]-self.purchase_values[sym])/self.purchase_values[sym]
                except TypeError:
                    print("Type Error - line 250")
                    print(sym)
                    print(self.current_holding_value)
                    print(current_coin.price(p, self.current_holding_value))
                    print(self.current_values[sym])
                    print(self.purchase_values[sym])
                    print(self.deltas[sym])
                    quit()
                if current_coin.sym in coin and self.deltas[sym] < -0.1:
                    allowed_pairs.append(sym)
                    
                #print(self.current_values[sym], self.purchase_values[sym])
        return allowed_pairs
    
    def day_trade(self):
        while(self.current_holding_value > 0.8):
            try:
                self.ETHUSD = self.coins['ETH'].usd_value
                # what are we holding?
                current_coin = self.coins[self.current_holding]
                
                # if we are holding an ALT coin - we want to sell it for profit
                if not current_coin.is_base:
                    # determine sell limit (current price + min_trade_threshold)
                    break_even_delta = 2 * .001 * self.purchase_values[current_coin.sym + 'ETH']
                    # check if sale is complete
                    if self.impatience_level > 0 and self.get_order_status():
                        self.current_holding = 'ETH'
                        continue # go to the next iteration of the while loop
                    waiting = datetime.now()-self.t0
                    # if its been <10 mins set limit to 5x
                    if waiting.total_seconds() < 5*60:
                        if self.impatience_level == 0:
                            # place new order at current_price
                            price = current_coin.sanitize('ETH', price = self.purchase_values[current_coin.sym + 'ETH'] + 5 * break_even_delta)
                            if self.trade_sell(current_coin.sym+'ETH', self.current_holding_qty, price):
                                self.current_holding = 'ETH'
                                continue
                            self.impatience_level = 1
                        else:
                            time.sleep(1)
                    # 10-15 mins - limit 4x
                    elif waiting.total_seconds() > 5*60 and self.impatience_level == 1:
                        print("Growing more impatient")
                        # cancel current order
                        self.cancel_order(current_coin.sym + 'ETH')
                        # place new order at current_price
                        price = current_coin.sanitize('ETH', price = self.purchase_values(current_coin.sym + 'ETH') + 4 * break_even_delta)
                        if self.trade_sell(current_coin.sym+'ETH', self.current_holding_qty, price):
                            self.current_holding = 'ETH'
                            continue
                        self.impatience_level = 2
                    # 15-20 mins - limit 3x
                    elif waiting.total_seconds() > 10*60 and self.impatience_level == 2:
                        print("Growing more impatient")
                        # cancel current order
                        self.cancel_order(current_coin.sym + 'ETH')
                        # place new order at current_price
                        price = current_coin.sanitize('ETH', price = self.purchase_values(current_coin.sym + 'ETH') + 3 * break_even_delta)
                        if self.trade_sell(current_coin.sym+'ETH', self.current_holding_qty, price):
                            self.current_holding = 'ETH'
                            continue
                        self.impatience_level = 3
                    # 20-25 min - limit 2x
                    elif waiting.total_seconds() > 15*60 and self.impatience_level == 3:
                        print("Growing more impatient")
                        # cancel current order
                        self.cancel_order(current_coin.sym + 'ETH')
                        # place new order at current_price
                        price = current_coin.sanitize('ETH', price = self.purchase_values(current_coin.sym + 'ETH') + 2 * break_even_delta)
                        if self.trade_sell(current_coin.sym+'ETH', self.current_holding_qty, price):
                            self.current_holding = 'ETH'
                            continue
                        self.impatience_level = 4
                    # 25 min + - limit 1x (let's just get our money back on this one)
                    else:
                        print("Fully impatient")
                        # cancel current order
                        self.cancel_order(current_coin.sym + 'ETH')
                        # place new order at current_price
                        price = current_coin.sanitize('ETH', price=self.purchase_values(current_coin.sym + 'ETH') + break_even_delta)
                        if self.trade_sell(current_coin.sym+'ETH', self.current_holding_qty, price):
                            self.current_holding = 'ETH'
                            continue
                        self.impatience_level = 5
                    # OR if we are greater than 1.1x AND market looks negative
                    current_price = current_coin.sanitize('ETH', price = current_coin.price('ETH', self.current_holding_value))
                    if current_price > self.purchase_values[current_coin.sym + 'ETH'] + break_even_delta:
                        (bid_depth, ask_depth) = current_coin.order_depth('ETH', self.current_holding_qty, False)
                        if ask_depth >= bid_depth:
                            # cancel current order
                            self.cancel_order(current_coin.sym + 'ETH')
                            # place new order at current_price
                            if self.trade_sell(current_coin.sym+'ETH', self.current_holding_qty, current_price):
                                self.current_holding = 'ETH'
                                continue
                            
                else:
                    # get conservative estimated value for each trade
                    allowed_pairs = self.update_values(current_coin.sym)
                    # see which are in favorable order depth
                    depth_dict = {}
                    for trade_pair in allowed_pairs:
                        (bid_depth, ask_depth) = current_coin.order_depth(trade_pair.replace(current_coin.sym,""), self.current_holding_qty, True)
                        depth_dict[trade_pair] = float(bid_depth)/float(ask_depth)
                    allowed_pairs = [c for c in depth_dict if depth_dict[c] > 2]
                    if len(allowed_pairs) == 0:
                        allowed_pairs.append(min([x + current_coin.sym for x in current_coin.pairs if x not in 'USDT'], key=(lambda k: self.deltas[k])))
                        # continue
                    # check if this has a pair that has decreased enough to be worth trading
                    best_trade = min(allowed_pairs, key=(lambda k: self.deltas[k]))
                    if best_trade not in depth_dict:
                        (bid_depth, ask_depth) = current_coin.order_depth(best_trade.replace(current_coin.sym,""), self.current_holding_qty, True)
                        depth_dict[best_trade] = float(bid_depth)/float(ask_depth)
                    if self.test:
                        min_trade_threshold = self.minimum_trade_value
                        self.current_holding_qty = self.max_trade_value/self.current_values[best_trade]
                    else:
                        min_trade_threshold = max(self.minimum_trade_value, current_coin.increment[best_trade] * current_coin.eth_value / current_coin.balance)
                        self.current_holding_qty = min(self.max_trade_value/self.current_values[best_trade], current_coin.balance/self.current_values[best_trade])
                    print("pair:{0:} price:{1:1.6f} delta: {2:1.6f} value increase:{3:1.6f} threshold:{4:1.6f} gap:{5:1.2f}% bid/ask:{6}".format(
                                best_trade, 
                                self.current_values[best_trade],
                                self.deltas[best_trade],
                                abs(self.deltas[best_trade]*self.current_holding_value),
                                min_trade_threshold,
                                current_coin.avg_gap(),
                                depth_dict[best_trade]), 
                                end="\r")
                    if abs(self.deltas[best_trade]*self.current_holding_value) > self.minimum_trade_value:
                        # check the order depth for expected market direction
                        if current_coin.avg_gap() < 0.55:
                            # if the bid depth is 20% higher than ask, market should soon trend up, so its okay to buy
                            print()
                            for s in self.current_values.keys():
                                self.purchase_values[s] = self.current_values[s]
                            print("Price: %f"%self.current_values[best_trade])
                            self.trade_buy(best_trade,
                                        current_coin.sanitize(best_trade, qty=self.current_holding_qty),
                                        current_coin.sanitize(best_trade, price=self.current_values[best_trade]))
                            self.impatience_level = 0


                
                    # # check if this pair's value increased (then we should sell back to base pair)
                    # best_trade = max(allowed_pairs, key=(lambda k: self.deltas[k]))
                    # if self.test:
                        # min_trade_threshold = self.minimum_trade_value
                        # self.current_holding_qty = self.max_trade_value/self.current_values[best_trade]
                    # else:
                        # min_trade_threshold = max(self.minimum_trade_value, current_coin.increment[best_trade] * current_coin.eth_value / current_coin.balance)
                        # self.current_holding_qty = min(self.max_trade_value/self.current_values[best_trade], current_coin.balance)
                    # try:
                        # (bid_depth, ask_depth) = current_coin.order_depth(best_trade.replace(current_coin.sym, ""), self.current_holding_qty, False)
                    # except KeyError:
                        # print("Key Error - line 245")
                        # print(current_coin.sym)
                        # print(current_coin.is_base)
                        # print(best_trade.replace(current_coin.sym, ""))
                        
                    # print("pair:{0:} price:{1:1.6f} delta:{2:1.6f} value increase:{3:1.6f} threshold:{4:1.6f} Gap:{5:1.2f}% ask/bid:{6}".format(
                                # best_trade, 
                                # self.current_values(best_trade),
                                # self.deltas[best_trade],
                                # abs(self.deltas[best_trade]*self.current_holding_value),
                                # min_trade_threshold,
                                # current_coin.avg_gap(),
                                # float(ask_depth)/float(bid_depth)), 
                                # end="\r")
                    # if self.deltas[best_trade]*self.current_holding_value > self.minimum_trade_value:
                        # if ask_depth >= bid_depth or self.deltas[best_trade]*self.current_holding_value > 5 * self.minimum_trade_value:
                            # # market probably is not going up much more
                            # print()
                            # for s in self.current_values.keys():
                                # self.purchase_values[s] = self.current_values[s]
                            # print("Price: %f"%self.current_values[best_trade])
                            # self.trade_sell(best_trade, 
                                            # current_coin.sanitize(best_trade, qty=self.current_holding_qty), 
                                            # current_coin.sanitize(best_trade, price=self.current_values[best_trade]))
            except json.decoder.JSONDecodeError:
                print("JSON Error...")
            time.sleep(0.1)
        
        
class Coin:
    def __init__(self, client, symbol):
        print("Adding Coin: %s"%symbol)
        self.client = client
        self.sym = symbol
        self.eth_value = 0
        self.btc_value = 0
        self.usd_value = 0
        self.min_price = {}
        self.max_price = {}
        self.min_qty = {}
        self.max_qty = {}
        self.increment = {}
        self.books = {}
        self.pairs = []
        self.balance = 0
        self.gap = collections.deque(5*[0], 5)
        # decide if this is a base pair
        if 'ETH' in self.sym or 'BTC' in self.sym:
            self.is_base = True
        else:
            self.is_base = False
        # set all the limits
        api_limits = self.client.get_exchange_info()
        symbol_limits = api_limits['symbols']
        possible_pairs = []
        for x in symbol_limits:
            if 'ETH' or 'BTC' in x['symbol']:
                possible_pairs.append(x['symbol'])
                self.increment[x['symbol']] = float(x['filters'][1]['stepSize'])
                self.min_price[x['symbol']] = float(x['filters'][0]['minPrice'])
                self.max_price[x['symbol']] = float(x['filters'][0]['maxPrice'])
                self.min_qty[x['symbol']] = float(x['filters'][1]['minQty'])
                self.max_qty[x['symbol']] = float(x['filters'][1]['maxQty'])
        # add defaul pairs
        if not self.is_base:
            self.add_pair('ETH')
        else:
            self.add_pair('USDT')
        
        # initial value update
        self.update_value()
        
    def __str__(self):
        return "{0:}: qty:{1:.6f} ETH value:{2:6f}".format(self.sym, self.balance, self.eth_value)
        
    def sanitize(self, sym, qty=None, price=None):
        if not sym:
            print("Need to give a symbol pair to sterelize!!!")
            return
        # if qty and qty > self.max_qty:
            # qty = self.max_qty
        # elif qty and qty < self.min_qty:
            # qty = self.min_qty
            
        # if price and price > self.max_price:
            # price = self.max_price
        # elif price and price < self.min_price:
            # price = self.min_price
        if qty:
            qty = float(int(qty/self.increment[sym])*self.increment[sym])
            
        if price:
            #price = float(int(price/self.increment)*self.increment)
            if qty:
                return (qty, price)
            else:
                return(price)
        elif qty:
            return(qty)
        else:
            return None
        
    def pair(self, symbol):
        if self.is_base:
            if symbol in 'BTC':
                return 'ETHBTC'
            elif symbol in 'USDT':
                return self.sym+'USDT'
            return symbol+self.sym
        return self.sym+symbol
        
    def add_pair(self, symbol):
        if symbol in self.sym:
            print("you can't trade with yourself")
            return False
        self.pairs.append(symbol)
        self.books[symbol] = {}
        self.books[symbol]['updated'] = datetime.now()-timedelta(days=1)
    
    def update_balance(self):
        self.balance = float(self.client.get_asset_balance(asset=self.sym)['free'])
    
    def update_books(self, symbol=None):
        #print("updating books for %s"%symbol)
        if symbol is None:
            # let's update everything
            _ = [self.update_books(s) for s in self.pairs]
        else:
            try:
                if (datetime.now() - self.books[symbol]['updated']).total_seconds() < 1:
                    return
                else:
                    self.books[symbol]['updated'] = datetime.now()
            except KeyError:
                print(symbol)
                print(self.books.keys())
                print(self.sym)
            temp_dict = self.client.get_order_book(symbol=self.pair(symbol)) 
            self.books[symbol]['bids'] = temp_dict['bids']
            self.books[symbol]['asks'] = temp_dict['asks']
            self.gap.appendleft(abs(float(self.books[symbol]['bids'][0][0]) - float(self.books[symbol]['asks'][0][0]))/float(self.books[symbol]['asks'][0][0]))

    def order_depth(self, sym, qty, buy_bool=True):
        self.update_books()
        # return bid and ask depth
        analysis_depth = qty * 20
        bids = [[float(x), float(y)] for [x, y, z] in self.books[sym]['bids']]
        asks = [[float(x), float(y)] for [x, y, z] in self.books[sym]['asks']]
        
        num_bid_orders = 0
        num_ask_orders = 0
        bid_area = 0
        ask_area = 0
        final_delta = 0
        
        if buy_bool:
            for a in asks[1:]:
                price_delta = abs(a[0] - asks[0][0])
                num_ask_orders += a[1]
                ask_area += price_delta*a[1]
                if num_ask_orders > analysis_depth:
                    break
            ask_area = ask_area/price_delta
            final_delta = price_delta

            for b in bids:
                price_delta = abs(b[0] - asks[0][0])
                num_bid_orders += b[1]
                bid_area += price_delta*b[1]
                if price_delta >= final_delta:
                    break
            bid_area = bid_area/price_delta
        else:
            for b in bids[1:]:
                price_delta = abs(b[0] - bids[0][0])
                num_bid_orders += b[1]
                bid_area += price_delta*b[1]
                if num_bid_orders > analysis_depth:
                    break
            bid_area = bid_area/price_delta
            final_delta = price_delta
            
            for a in asks:
                price_delta = abs(a[0] - bids[0][0])
                num_ask_orders += a[1]
                ask_area += price_delta*a[1]
                if price_delta >= final_delta:
                    break
            ask_area = ask_area/price_delta
                    
        # if buy is bigger, expect price to trend up, if ask is bigger expect price to trend down
        return (bid_area, ask_area)
            
        
    def update_value(self):
        self.update_books()
        self.update_balance()
        if 'ETH' in self.sym: 
            self.eth_value = self.balance
            self.usd_value = self.balance * float(self.books['USDT']['asks'][0][0])
        else: # its an alt
            self.eth_value = self.balance * float(self.books['ETH']['asks'][0][0])
            self.usd_value = None
    
    def avg_gap(self):
        return 100 * sum(self.gap)/len(self.gap)
    
    def price(self, symbol, base_value):
        self.update_books(symbol)
        
        if self.is_base:
            #then we want to buy
            trades = [[float(x), float(y)] for [x, y, z] in self.books[symbol]['asks']]
            quantity = base_value/trades[0][0]
        else:
            # then we want to sell
            trades = [[float(x), float(y)] for [x, y, z] in self.books[symbol]['bids']]
            quantity = base_value/trades[0][0]
        sum = 0
        count = 0
        # print(symbol)
        # print(trades)
        for i in trades:
            sum += i[1]
            count += 1
            if sum >= quantity*2:
                # print("%s expect %d trades @ price: %f" %(symbol, count, i[0]))
                # print(count, i[0])
                # print(trades)
                return self.sanitize(self.pair(symbol), price=i[0])
        return trades[-1][0]
            

if __name__ == '__main__':
    # enter your key and secret key
    key = 'xxxx'
    secret = 'xxxx'
    dogebot = VolatilityBot(key, secret)
    # dogebot.get_balance()
    dogebot.threshold(time_between_trades = 1)
    dogebot.threshold()
    dogebot.day_trade()
