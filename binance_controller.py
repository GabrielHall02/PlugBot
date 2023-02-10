from binance.client import Client
from mongo_controller import MongoController
import requests
import json
import hmac
import hashlib
import time
from dotenv import load_dotenv
import os


class BinanceController:
    def __init__(self):
        self.controller = MongoController()
        load_dotenv()
        self.api_key = os.getenv('API_KEY')
        self.api_secret = os.getenv('SECRET_KEY')
        self.api_key, self.api_secret = self.controller.get_binance_key_pair()
        self.client = Client(self.api_key, self.api_secret)
        self.binance_url = "https://api4.binance.com"

    def get_coin_networks(self, coin):
        url = self.binance_url + "/sapi/v1/capital/config/getall"
        # Create a timestamp
        timestamp = int(time.time() * 1000)

        # Create the signature
        query_string = f"timestamp={timestamp}"
        signature = hmac.new(self.api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

        # Send the GET request
        headers = { "X-MBX-APIKEY": self.api_key }
        response = requests.get(url + "?" + query_string + "&signature=" + signature, headers=headers)

        # Parse the JSON response
        response_json = json.loads(response.text)

        # Search json for coin = coin
        coin_networks = {}
        for i in range(len(response_json)):
            if response_json[i]["coin"] == coin:
                for j in range(len(response_json[i]["networkList"])):
                    coin_networks[response_json[i]["networkList"][j]["network"]] = response_json[i]["networkList"][j]["name"]
                break
        
        return coin_networks

    def get_deposit_address(self, symbol, network=None):
        """Returns the deposit address for a specific cryptocurrency"""
        if network is None:
            self.get_coin_networks(symbol)

        return self.client.get_deposit_address(coin=symbol, network=network)
    
    def get_deposit_history(self, symbol):
        """Returns the deposit history for a specific cryptocurrency"""
        return self.client.get_deposit_history(coin=symbol)
    
    def get_deposit_by_txid(self, symbol, txid):
        """Check if the deposit with txid is in the deposit history"""
        # Get deposit history
        deposit_history = self.get_deposit_history(symbol)
        # Search for txid
        for i in range(len(deposit_history)):
            if deposit_history[i]["txId"] == txid:
                return deposit_history[i]
        return None
    
    def get_coin_price_EUR(self, coin):
        """Returns the price of a specific cryptocurrency"""
        currency = "EUR"
        symbols = self.get_all_exchange_symbols()

        # Find the symbol that contains the coin and the currency
        for i in range(len(symbols)):
            if coin in symbols[i] and currency in symbols[i]:
                return self.client.get_symbol_ticker(symbol=symbols[i])["price"]

        return None

    def get_all_exchange_symbols(self):
        """Returns all exchange symbols"""
        return [x["symbol"] for x in self.client.get_exchange_info()["symbols"]]

def main():
    binance_controller = BinanceController()
    print(binance_controller.get_deposit_by_txid("USDT", "Internal transfer 128771144816"))

if __name__ == "__main__":
    main()
