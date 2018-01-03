from binance.client import Client
import pprint
from itertools import chain
import time
import operator
from datetime import datetime

# this returns a list of dictionaries {'id':123456, 'price':9876, 'qty':123, 'time':utcUnixTime}
# ethbtc = client.get_recent_trades(symbol='ETHBTC')

# this returns a dictionary 
# {'lastUpdateID':123456, 
#  'bids':[[cost, qty, []], [cost, qty, []], ...], 
#  'asks':[[cost, qty, []], [cost, qty, []], ...]}

# print('Bids (buy):')
# pp.pprint(ethbtc['bids'][:10])
# print('Asks (sell):')
# pp.pprint(ethbtc['asks'][:10])
# 
# this will get the current price of every pair on binance
# [{'symbol':'ETHBTC', 'price':12345}, {'symbol':'LTCBTC', 'price':123}, ...]
# prices = client.get_all_tickers()
# print("Symbol\t\tPrice")
# for i in prices:
	# print("%s:\t\t%f"%(i['symbol'], float(i['price'])))


class BinanceBot:
	def __init__(self, api_key, api_secret):
		self.pp = pprint.PrettyPrinter(indent=4)
		self.api_secret = api_secret
		self.api_key = api_key
		self.client = Client(api_key, api_secret)
		self.what_is_allowed()
		self.balance = {}
		self.ETHBTC_value = 0
		self.current_holding = 'ETH'
		self.current_holding_qty = 2  # this is in the above
		self.current_holding_value = 2  # this is in ETH
		self.pairs_of_interest = [('REQ','ETH'), ('REQ','BTC'),
								  ('LTC','ETH'), ('LTC','BTC'),
								  ('NEO','ETH'), ('NEO','BTC'),
								  ('IOTA','ETH'), ('IOTA','BTC'),
								  ('XLM','ETH'), ('XLM','BTC')]
		self.list_of_pairs_of_interest = [x+y for (x,y) in self.pairs_of_interest]

	def what_is_allowed(self):
		api_limits = self.client.get_exchange_info()
		self.rate_limits = api_limits['rateLimits']
		for d in self.rate_limits:
			if 'REQUESTS' in d['rateLimitType']:
				print("Max Requests per %s: %d"%(d['interval'], d['limit']))
			elif 'ORDERS' in d['rateLimitType']:
				print("Max Orders per %s: %d"%(d['interval'], d['limit']))	
		
	def get_current_prices(self):
		current_values = {}
		all_tickers = self.client.get_all_tickers()
		for i in all_tickers:
			if i['symbol'] in self.list_of_pairs_of_interest:
				current_values[i['symbol']] = i['price']
			if 'ETHBTC' in i['symbol']:
				self.ETHBTC_value = float(i['price'])
		return current_values
		
	def trade_buy(self, trade_pair, quantity, price=None):
		if price is None: # market order
			# self.current_order = self.client.order_markey_buy(trade_pair, quantity)
			pass
		#the below chunk is only needed for fake trading
		print("BUY!!! %s: qty: %d price: %f"%(trade_pair, quantity, price))
		self.current_holding = trade_pair[:-3]
		self.current_holding_qty = quantity
		print("now holding: %s, qty: %f, value: %f"%(self.current_holding, self.current_holding_qty, self.current_holding_value))
		return
		
	def trade_sell(self, trade_pair, quantity, price=None):
		if price is None: # market order
			# self.current_order = self.client.order_markey_sell(trade_pair, quantity)
			pass
		print("SELL!!! %s: qty: %d price: %f"%(trade_pair, quantity, price))
		if 'BTC' in trade_pair:
			self.current_holding = 'BTC'
			self.current_holding_qty = quantity*price
			self.current_holding_value = (1/self.ETHBTC_value)*self.current_holding_qty
		else:
			self.current_holding = 'ETH'
			self.current_holding_qty = quantity*price
			self.current_holding_value = self.current_holding_qty
		print("now holding: %s, qty: %f, value: %f"%(self.current_holding, self.current_holding_qty, self.current_holding_value))
		return
		
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
		print("Time: %s\t Value: %f Total Fees: %f"%(datetime.now(), self.current_holding_value, self.total_fees))
		super().trade_buy(trade_pair, quantity, price)
		
	def trade_sell(self, trade_pair, quantity, price=None):
		print("Time: %s\t Value: %f Total Fees: %f"%(datetime.now(), self.current_holding_value, self.total_fees))
		super().trade_sell(trade_pair, quantity, price)
		
	def day_trade(self):
		while(1):
			time.sleep(self.wait_time)
			best_trade = self.check_value_delta()
			# print trading pair and value increase (in ether)
			# print(best_trade, self.deltas[best_trade]*self.current_holding_value)
			# if the value is above our comfort threshold
			if self.deltas[best_trade]*self.current_holding_value > self.minimum_trade_value:
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
				
				
				# if we need to buy something in ETH
				# if 'ETH' in best_trade:
					# # We are holding something other than ETH
					# if 'ETH' not in self.current_holding:
						# # we are holding BTC
						# if 'BTC' in self.current_holding: 
							# # # so lets covert that to ETH first
							# # self.trade_buy('ETH'+self.current_holding, self.ETHBTC_value*self.current_holding_qty, self.ETHBTC_value)
						# # we are holding something other than ETH or BTC
						# else:
							# self.trade_sell(self.current_holding+'ETH', self.current_holding_qty, float(self.current_values[self.current_holding+'ETH']))
						# self.trade_buy(best_trade, self.current_holding_value/price, price)
					# # We already have ETH
					# else:
						# self.trade_buy(best_trade, self.current_holding_qty/price, price)
				# # we need to buy something in BTC
				# elif 'BTC' in best_trade:
					# # if we don't have BTC already
					# if 'BTC' not in self.current_holding:
						# self.trade_sell(self.current_holding+'BTC', self.current_holding_qty, float(self.current_values[self.current_holding+'BTC']))
					# self.trade_buy(best_trade, self.current_holding_qty/price, price)
				# self.purchase_values = self.get_current_prices()
			
			
		
		
if __name__ == '__main__':

	dogebot = VolatilityBot(key, secret)
	# dogebot.get_balance()
	dogebot.threshold(time_between_trades = 60)
	dogebot.threshold()
	dogebot.day_trade()
	