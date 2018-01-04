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
		self.balance = {}
		self.sym_lot_size = {}
		self.ETHBTC_value = 0
		self.ETHUSDT = 0
		self.current_holding = 'ETH'
		self.current_holding_qty = 2  # this is in the above
		self.current_holding_value = 2  # this is in ETH
		self.pairs_of_interest = [('REQ','ETH'), ('REQ','BTC'),
								  ('LTC','ETH'), ('LTC','BTC'),
								  ('NEO','ETH'), ('NEO','BTC'),
								  ('IOTA','ETH'), ('IOTA','BTC'),
								  ('XLM','ETH'), ('XLM','BTC'),
								  #('NAV','ETH'), ('NAV','BTC'), # volume is too low for now
								  ('FUN','ETH'), ('FUN','BTC')]
		self.list_of_pairs_of_interest = [x+y for (x,y) in self.pairs_of_interest]
		self.what_is_allowed()

	def what_is_allowed(self):
		api_limits = self.client.get_exchange_info()
		self.rate_limits = api_limits['rateLimits']
		for d in self.rate_limits:
			if 'REQUESTS' in d['rateLimitType']:
				print("Max Requests per %s: %d"%(d['interval'], d['limit']))
			elif 'ORDERS' in d['rateLimitType']:
				print("Max Orders per %s: %d"%(d['interval'], d['limit']))	
		symbol_limits = api_limits['symbols']
		for coin in symbol_limits:
			if coin['symbol'] in self.list_of_pairs_of_interest+['ETHBTC']:
				self.sym_lot_size[coin['symbol']] = float(coin['filters'][1]['stepSize'])
		print('Minimum Lot Size by Symbol')
		self.pp.pprint(self.sym_lot_size)
		
	def get_current_prices(self):
		current_values = {}
		all_tickers = self.client.get_all_tickers()
		for i in all_tickers:
			if i['symbol'] in self.list_of_pairs_of_interest:
				current_values[i['symbol']] = i['price']
			elif 'ETHBTC' in i['symbol']:
				self.ETHBTC_value = float(i['price'])
			elif 'ETHUSDT' in i['symbol']:
				self.ETHUSDT = float(i['price'])
		# self.pp.pprint(current_values)
		return current_values
		
	def document_transaction(self, data_list, filename = "c:\\git\\dogebot\\trade_documentation.csv"):
		write_headers = False
		if not os.path.isfile(filename):
			write_headers = True
		with open(filename, 'a', newline='') as f:
			writer = csv.writer(f)
			if write_headers:
				writer.writerow(['date', 'holding symbol', 'trade pair', 'type', 'quantity', 'price', 'fee', 'value (eth), value (usd)'])
			# data_list = ['date', 'holding symbol', 'trade pair', 'type', 'quantity', 'price', 'fee', 'value (eth), 'value (usd)']
			writer.writerow(data_list)
		
	def trade_buy(self, trade_pair, qty, bid_price=None):
		if bid_price is None: # market order
			self.current_order = self.client.order_market_buy(symbol=trade_pair, quantity=qty)
		else:
			self.current_order = self.client.order_limit_buy(symbol=trade_pair,
															 quantity=qty,
															 price=str(bid_price))
		orderID = self.current_order['orderId']
		order_price = float(self.current_order['price'])
		# let's make sure this works before adding transactions
		while(self.current_order['status'] not in "FILLED"): 
			order = self.client.get_order(symbol=trade_pair, orderId=orderID)
			time.sleep(1)
			
		print("BUY!!! %s: qty: %d price: %f"%(trade_pair, qty, bid_price))
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
		
		return True
		
	def trade_sell(self, trade_pair, qty, ask_price=None):
		if ask_price is None: # market order
			self.current_order = self.client.order_market_sell(symbol=trade_pair, quantity=qty)
		else: # non-market order
			self.current_order = self.client.order_limit_sell(symbol=trade_pair,
															  quantity=qty,
															  price=str(ask_price))
		orderID = self.current_order['orderId']
		order_price = float(self.current_order['price'])
		# let's make sure this works before adding transactions
		while(self.current_order['status'] not in "FILLED"): 
			order = self.client.get_order(symbol=trade_pair, orderId=orderID)
			time.sleep(1)
			# TODO: something about EXPIRED or CANCELLED status, for now it will hang
			
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
		
		return True
		
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
		
class VolatilityBot(BinanceBot):
	def __init__(self, api_key, api_secret):
		super().__init__(api_key, api_secret)
		self.purchase_values = self.get_current_prices()
		self.current_values = {}
		self.deltas = {}
		self.wait_time = 1
		self.trade_fee = 0.001  # 0.1% fee
		self.total_fees = 0
		self.minimum_trade_value = self.current_holding_value * (2 * self.trade_fee) # this is in ETH
		# there is probably a way to actually lookup the transaction fees instead of assuming
		
	def collect_info(self):
		all_tickers = client.get_all_tickers()
		# for i in all_tickers:
			# if 'ETHBTC' in i['symbol']:
				# ethbtc_price = i['price']
		# ethbtc = client.get_order_book(symbol='ETHBTC')
		# print("All Tickers Price: %s"% ethbtc_price)
		# print("Highest Bid Price: %s"%ethbtc['bids'][0][0])	
		# print("Lowest Ask Price: %s"%ethbtc['asks'][0][0])	
		for t in all_tickers:
			if t['symbol'] in self.list_of_pairs_of_interest:
				pass

	def check_value_delta(self):
		old = self.purchase_values
		self.current_values = self.get_current_prices()
		self.current_values['ETHBTC'] = self.ETHBTC_value
		new = self.current_values
		# if we are holding something other than ETH, adjust our value
		if 'ETH' not in self.current_holding:
			if 'BTC' in self.current_holding:
				self.current_holding_value = self.current_holding_qty*float(self.current_values['ETHBTC'])
			else:
				self.current_holding_value = self.current_holding_qty*float(self.current_values[self.current_holding+'ETH'])
		for p in self.list_of_pairs_of_interest:
			self.deltas[p] = (float(old[p])-float(new[p]))/float(old[p])
		return max(self.deltas.keys(), key=(lambda k: self.deltas[k]))
		
	def threshold(self, min_price_in_eth=None, time_between_trades=None):
		if min_price_in_eth:
			self.minimum_trade_value = min_price_in_eth
		if time_between_trades:
			self.wait_time = time_between_trades
		else:
			print("Minimum Trade Value (ETH): %f"%self.minimum_trade_value)
			print("Wait Time between price lookup (sec):%d"%self.wait_time)
		
	def trade_buy(self, trade_pair, quantity, price=None):
		quantity = int(quantity/self.sym_lot_size[trade_pair])*self.sym_lot_size[trade_pair]
		print("Time: %s\t Value: %f Total Fees: %f"%(datetime.now(), self.current_holding_value, self.total_fees))
		super().trade_buy(trade_pair, quantity, price)
		
	def trade_sell(self, trade_pair, quantity, price=None):
		quantity = int(quantity/self.sym_lot_size[trade_pair])*self.sym_lot_size[trade_pair]
		print("Time: %s\t Value: %f Total Fees: %f"%(datetime.now(), self.current_holding_value, self.total_fees))
		super().trade_sell(trade_pair, quantity, price)
		
	def day_trade(self):
		while(1):
			time.sleep(self.wait_time)
			best_trade = self.check_value_delta()
			if self.minimum_trade_value < self.sym_lot_size[best_trade]*float(self.current_values[best_trade]):
				min_trade_threshold = self.sym_lot_size[best_trade]*float(self.current_values[best_trade])
			else:
				min_trade_threshold = self.minimum_trade_value
			# print trading pair and value increase (in ether)
			print("pair:{0:} value increase:{1:1.6f} threshold:{2:1.6f}".format(best_trade, 
																	      self.deltas[best_trade]*self.current_holding_value,
																		  min_trade_threshold), end="\r")
			# if the value is above our comfort threshold
			if self.deltas[best_trade]*self.current_holding_value > min_trade_threshold:
				price = float(self.current_values[best_trade])
				base_pair = best_trade[-3:]
				# if we are holding something in the trade pair - then let's do it!
				if self.current_holding in best_trade:
					# if we are holding the base pair - we want to buy
					if self.current_holding in base_pair:
						self.total_fees += self.current_holding_value*self.trade_fee
						self.current_holding_value -= self.current_holding_value*self.trade_fee
						self.trade_buy(best_trade, self.current_holding_qty*(1-self.trade_fee)/price, price)
					# else we already have this :/
				# we are not holding any part of this pair, we need to make sure two trades is worthwhile
				elif  self.deltas[best_trade]*self.current_holding_value > self.minimum_trade_value * 2:
					self.trade_sell(self.current_holding+base_pair, self.current_holding_qty, float(self.current_values[self.current_holding+base_pair]))
					if 'ETH' in base_pair:
						self.total_fees += self.current_holding_value*self.trade_fee
						self.current_holding_value -= self.current_holding_value*self.trade_fee
						self.trade_buy(best_trade, self.current_holding_qty*(1-self.trade_fee)/price, price)
					else: # we need the value of BTC in ETH
						self.total_fees += self.current_holding_value*self.trade_fee
						self.current_holding_value -= self.current_holding_value*self.trade_fee
						self.trade_buy(best_trade, self.current_holding_qty*(1-self.trade_fee)/price, price)
				#guess we will wait then	
				else: 
					pass

		
if __name__ == '__main__':
	# enter your key and secret key
	key = 'xxxx'
	secret = 'xxxx'
	dogebot = VolatilityBot(key, secret)
	# dogebot.get_balance()
	dogebot.threshold(time_between_trades = 1)
	dogebot.threshold()
	dogebot.day_trade()
	
