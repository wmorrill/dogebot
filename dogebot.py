from binance.client import Client
from binance.enums import *
import pprint
from itertools import chain
import time
import operator
from datetime import datetime
import csv
import os

class BinanceBot:
	def __init__(self, api_key, api_secret):
		self.pp = pprint.PrettyPrinter(indent=4)
		self.api_secret = api_secret
		self.api_key = api_key
		self.client = Client(api_key, api_secret)
		self.coins = {}
		self.current_holding = 'ETH'
		self.current_holding_qty = 1  # this is in the above
		self.current_holding_value = 1  # this is in ETH
		self.coins_of_interest = ['REQ', 'LTC', 'NEO', 'IOTA', 'XLM', 'NAV', 'FUN']
		self.what_is_allowed()
		self.coins['ETH'] = Coin(client=self.client, symbol='ETH')
		self.coins['BTC'] = Coin(client=self.client, symbol='BTC')
		for coin in self.coins_of_interest:
			self.coins[coin] = Coin(client=self.client, symbol=coin)
			self.coins['ETH'].add_pair(coin)
			self.coins['BTC'].add_pair(coin)
			
	def what_is_allowed(self):
		api_limits = self.client.get_exchange_info()
		self.rate_limits = api_limits['rateLimits']
		for d in self.rate_limits:
			if 'REQUESTS' in d['rateLimitType']:
				print("Max Requests per %s: %d"%(d['interval'], d['limit']))
			elif 'ORDERS' in d['rateLimitType']:
				print("Max Orders per %s: %d"%(d['interval'], d['limit']))	
		symbol_limits = api_limits['symbols']
		
	def document_transaction(self, data_list, filename = "c:\\git\\dogebot\\trade_documentation.csv"):
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
			self.current_order = self.client.order_market_buy(symbol=trade_pair, quantity=qty)
		else:
			self.current_order = self.client.order_limit_buy(symbol=trade_pair,
															 quantity=qty,
															 price=str(float(bid_price)))
		orderID = self.current_order['orderId']
		
		# let's make sure this works before moving on
		while(self.current_order['status'] not in "FILLED"): 
			self.current_order = self.client.get_order(symbol=trade_pair, orderId=orderID)
			time.sleep(1)
		
		order_price = float(self.current_order['price'])		
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
						 self.current_holding_value*self.ETHUSDT]
		self.document_transaction(documentation)
		
		return order_price
		
	def trade_sell(self, trade_pair, qty, ask_price=None):
		if ask_price is None: # market order
			self.current_order = self.client.order_market_sell(symbol=trade_pair, quantity=qty)
		else: # non-market order
			print("{0}, type:{1}".format(str(float(ask_price)), type(str(float(ask_price)))))
			self.current_order = self.client.order_limit_sell(symbol=trade_pair,
															  quantity=qty,
															  price=str(float(ask_price)))
		orderID = self.current_order['orderId']
		
		# let's make sure this works before adding transactions
		while(self.current_order['status'] not in "FILLED"): 
			self.current_order = self.client.get_order(symbol=trade_pair, orderId=orderID)
			time.sleep(1)
			# TODO: something about EXPIRED or CANCELLED status, for now it will hang
			
		order_price = float(self.current_order['price'])
		print("SELL!!! %s: qty: %d price: %f"%(trade_pair, qty, ask_price))
		if 'BTC' in trade_pair:
			self.current_holding = 'BTC'
			self.current_holding_qty = qty*ask_price
			self.current_holding_value = (1/self.ETHBTC_value)*self.current_holding_qty
		else:
			self.current_holding = 'ETH'
			self.current_holding_qty = qty*ask_price
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
						 self.current_holding_value*self.ETHUSDT]
		self.document_transaction(documentation)
		
		return order_price
		
	def get_balance(self):
		unique_coins = set(list(chain.from_iterable(self.pairs_of_interest)))
		for coin in unique_coins:
			self.balance[coin] = self.client.get_asset_balance(asset=coin)
		print("current Holdings")
		self.pp.pprint(self.balance)
		
	def cancel_open_orders(self):
		for (x,y) in self.pairs_of_interest:
			order = self.client.get_open_orders(x+y)
			result = self.client.cancel_order(order[0], order[1]) # this is a guess on array position, need to validate
			
	def get_recent_trades(self, symbol='ETHBTC'):
		recent_trades = client.get_recent_trades(symbol='ETHBTC')
		# this returns a dictionary 
		# {'lastUpdateID':123456, 
		# 'bids':[[cost, qty, []], [cost, qty, []], ...], 
		# 'asks':[[cost, qty, []], [cost, qty, []], ...]}

		print('Bids (buy):')
		pp.pprint(recent_trades['bids'][:10])
		print('Asks (sell):')
		pp.pprint(recent_trades['asks'][:10])
		
	def get_open_orders(self, sym=None):
		"""
		orders = {symbol: { 'bids':[
							[str(highest_price), str(qty)],
							[str(price--), str(qty)],...] 
							'asks':[
							[str(lowest_price), str(qty)],
							[str(price++), str(qty)],...] 
						   }
				  }
		"""
		orders = {}
		if sym:
			orders[sym] = self.client.get_order_book(symbol='ETHBTC')
		else:
			for sym in self.list_of_pairs_of_interest:
				orders[sym] = self.client.get_order_book(symbol=sym)
		# self.pp.pprint(orders)
		return orders
			
		
class VolatilityBot(BinanceBot):
	def __init__(self, api_key, api_secret):
		super().__init__(api_key, api_secret)
		self.purchase_values = {}
		self.current_values = {}
		self.deltas = {}
		self.wait_time = 1
		self.trade_fee = 0.001  # 0.1% fee
		self.total_fees = 0
		self.max_trade_value = 2  # ETH
		self.minimum_trade_value = self.current_holding_value * (2 * self.trade_fee) # this is in ETH
				
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
		#return super().trade_buy(trade_pair, quantity, price)
		
	def trade_sell(self, trade_pair, quantity, price=None):
		print("Time: %s\t Value: %f Total Fees: %f"%(datetime.now(), self.current_holding_value, self.total_fees))
		print("Sell: %s x %f @ %s"%(trade_pair, quantity, str(price)))
		#return super().trade_sell(trade_pair, quantity, price)
		
	def day_trade(self):
		while(1):
			# what are we holding?
			current_coin = self.coins[self.current_holding]
			# get conservative estimated value for each trade
			for p in current_coin.pairs:
				if p in "USDT":
					continue
				sym = current_coin.pair(p)
				self.current_values[sym] = current_coin.price(p, self.current_holding_value)
				if sym not in self.purchase_values.keys():
					# print(sym, self.purchase_values.keys())
					self.purchase_values[sym] = self.current_values[sym]
				# print(sym, self.current_values[sym], self.purchase_values[sym])
				try:
					self.deltas[sym] = (self.current_values[sym]-self.purchase_values[sym])/self.purchase_values[sym]
				except TypeError:
					self.purchase_values[sym] = self.current_values[sym]
			if not current_coin.is_base:
				# check if this pair's value increased (then we should sell back to base pair)
				best_trade = max(self.deltas.keys(), key=(lambda k: self.deltas[k]))
				min_trade_threshold = max(self.minimum_trade_value, current_coin.increment[best_trade] * current_coin.eth_value / current_coin.balance)
				self.current_holding_qty = min(self.max_trade_value/self.current_values[best_trade], current_coin.balance)
				print("pair:{0:} value increase:{1:1.6f} threshold:{2:1.6f}".format(best_trade, 
																		  self.deltas[best_trade]*self.current_holding_value,
																		  min_trade_threshold), end="\r")
				if self.deltas[best_trade]*self.current_holding_value > self.minimum_trade_value:
					self.trade_sell(best_trade, current_coin.sterilize(best_trade, qty=self.current_holding_qty))
			else:
				# check if this has a pair that has decreased enough to be worth trading
				best_trade = min(self.deltas.keys(), key=(lambda k: self.deltas[k]))
				min_trade_threshold = max(self.minimum_trade_value, current_coin.increment[best_trade] * current_coin.eth_value / current_coin.balance)
				self.current_holding_qty = min(self.max_trade_value/self.current_values[best_trade], current_coin.balance/self.current_values[best_trade])
				print("pair:{0:} value increase:{1:1.6f} threshold:{2:1.6f}".format(best_trade, 
																		  abs(self.deltas[best_trade]*self.current_holding_value),
																		  min_trade_threshold), end="\r")
				if abs(self.deltas[best_trade]*self.current_holding_value) > self.minimum_trade_value:
					self.purchase_values[best_trade] = self.trade_buy(best_trade, current_coin.sterilize(best_trade, qty=self.current_holding_qty))
			# decide if that price is worthwhile to trade (if so we should buy)
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
		# decide if this is a base pair
		if 'ETH' in self.sym or 'BTC' in self.sym:
			self.is_base = True
		else:
			self.is_base = False
			self.add_pair('ETH')
			self.add_pair('BTC')
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
			self.add_pair('BTC')
		else:
			if self.sym in 'BTC':
				self.add_pair('ETH')
				self.add_pair('USDT')
			else:
				self.add_pair('BTC')
				self.add_pair('USDT')
		
		# initial value update
		self.update_value()
		
	def __str__():
		return "{0:}: qty:{1:.6f} ETH value:{2:6f}".format(self.sym, self.balance, self.eth_value)
		
	def sterilize(self, sym, qty=None, price=None):
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
	
	def update_balance(self):
		self.balance = float(self.client.get_asset_balance(asset=self.sym)['free'])
	
	def update_books(self, symbol=None):
		#print("updating books for %s"%symbol)
		if symbol is None:
			# let's update everything
			update_list = self.pairs
		else:
			# lets just check that one to be efficient
			update_list = [symbol,]
		for antagonist in update_list:
			self.books[antagonist] = self.client.get_order_book(symbol=self.pair(antagonist)) 

	def update_value(self):
		self.update_books()
		self.update_balance()
		if 'ETH' in self.sym: 
			self.eth_value = self.balance
			self.btc_value = self.balance * float(self.books['BTC']['asks'][0][0])
			self.usd_value = self.balance * float(self.books['USDT']['asks'][0][0])
		elif 'BTC' in self.sym:
			self.eth_value = self.balance / float(self.books['ETH']['asks'][0][0])
			self.btc_value = self.balance
			self.usd_value = self.balance * float(self.books['USDT']['asks'][0][0])
		else: # its an alt
			self.eth_value = self.balance * float(self.books['ETH']['asks'][0][0])
			self.btc_value = self.balance * float(self.books['BTC']['asks'][0][0])
			self.usd_value = None
			
	def price(self, symbol, base_value):
		self.update_books(symbol)
		
		if self.is_base:
			#then we want to buy
			quantity = base_value
			trades = [[float(x), float(y)] for [x, y, z] in self.books[symbol]['asks']]
		else:
			# then we want to sell
			quantity = self.sterilize(self.pair(symbol), qty=base_value/self.books[symbol]['asks'][0])
			trades = [[float(x), float(y)] for [x, y, z] in self.books['bids']]
		sum = 0
		count = 0
		# print(symbol)
		# print(trades)
		for i in trades:
			sum += i[1]
			count += 1
			if sum >= quantity*1.1:
				# print("expect %d trades @ price: %f" %(count, i[0]))
				return self.sterilize(self.pair(symbol), price=i[0])
		return 
			

if __name__ == '__main__':
	# enter your key and secret key
	key = 'xxxx'
	secret = 'xxxx'
	dogebot = VolatilityBot(key, secret)
	# dogebot.get_balance()
	dogebot.threshold(time_between_trades = 1)
	dogebot.threshold()
	dogebot.day_trade()
