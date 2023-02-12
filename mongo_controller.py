from pymongo import MongoClient
from datetime import datetime
from bson.objectid import ObjectId
from dotenv import load_dotenv
import os

class MongoController:
    def __init__(self):
        load_dotenv()
        mongo_url = os.getenv('MONGO_URL')
        self.client = MongoClient(mongo_url)
        self.db = self.client["Landohub"]
        self.addresses = self.db["Addresses"]
        self.finance = self.db["Finance"]
        self.tickets = self.db["Tickets"]
        self.clients = self.db["Clients"]
        self.prices = self.db["Prices"]
        self.accounts = self.db["Accounts"] 
        self.garbage_accounts = self.db["GarbageAccounts"]
        self.checkout_sessions = self.db["CheckoutSessions"]
    
    def get_revolut_address(self):
        """Returns the revolut address from the database"""
        return self.addresses.find_one({'key': 'revolut'})['address']

    def get_binance_payid_address(self):
        """Returns the binance payID address from the database"""
        return self.addresses.find_one({'key': 'binancePayId'})['address']
    
    # ACCOUNT METHODS
    
    def get_account_prices(self):
        """Returns the prices from the database"""
        return list(self.prices.find({}, {"_id": 0}).sort("step", 1))
    
    def get_n_accounts_price(self, number_of_accounts):
        """Returns the price of an amount of accounts"""
        # Get the prices from the database
        prices = self.get_account_prices()
        # Get the price for the number of accounts
        if number_of_accounts >= prices[-1]["step"]:
            return prices[-1]["price"]
        for i in range(len(prices)-1):
            if prices[i]["step"] <= number_of_accounts and number_of_accounts < prices[i+1]["step"]:
                return prices[i]["price"]

    def set_account_price(self, step, price):
        """Sets the prices in the database"""
        # Check if step is in the database
        # If it is update the price
        if self.prices.find_one({"step":step}, {"_id":0, "step":1, "price":1}):
            # Update the price
            self.prices.update_one({"step":step}, {"$set": {"price":price}})
        else:
            # Add the step and the price
            self.prices.insert_one({"step":step, "price":price})
    
    def del_account_price(self, step):
        """Deletes the price from the database"""
        self.prices.delete_one({"step":step})

    def get_account(self, account):
        """Returns an account from the database"""
        return self.accounts.find_one({"account":account})

    def get_number_of_available_accounts(self):
        """Returns the count of available accounts from the database"""
        return self.accounts.count_documents({"status":"cartable"})

    def get_n_available_accounts(self, n):
        """Returns n available accounts from the database"""
        return list(self.accounts.find({"status":"cartable"}).limit(n))
    
    def update_account_status(self, account, status):
        """Updates the state of an account"""
        self.accounts.update_one({"account":account}, {"$set": {"status":status}})
    
    def garbage_account(self, account):
        """Moves an account to the garbage collection"""
        self.garbage_accounts.insert_one(self.accounts.find_one({"account":account}))
        self.accounts.delete_one({"account":account})

    def get_all_accounts(self):
        """Returns all accounts from the database"""
        return list(self.accounts.find({}))

    def get_all_bad_accounts(self):
        """Returns all bad accounts from the database"""
        return self.accounts.find({"status":"bad_account"})

    def get_all_sold_accounts(self):
        """Returns all sold accounts from the database"""
        return list(self.accounts.find({"status":"sold"}))

    def get_all_uncartable_accounts(self):
        """Returns all uncartable accounts from the database"""
        return self.accounts.find({"status":"uncartable"})
    
    def insertOne_cartable_account(self, account):
        """Inserts a list of accounts into the database"""
        self.accounts.insert_one({"account":account, "status":"cartable"})

    # FINANCE METHODS

    def insert_finance_statement(self, statement):
        """Inserts a finance statement into the database"""
        self.finance.insert_one(statement)

    def basic_finance_dashboard(self, start_date, end_date):
        """Returns Total Revenue, Exepenses, Profit, Profit Margin, Number of Accounts Sold"""
        # Should also return Revenue, Expense, and Profit by payment method

        # Get all the finance statements
        finance_statements = self.finance.find({"Date":{"$gte":start_date, "$lte":end_date}})

        # Initialize the variables
        revenue = {"total":0}
        expenses = {"total":0}
        profit = {}
        n_accounts_sold = 0
        
        # Iterate through the finance statements
        for statement in finance_statements:
            # Add the revenue, expenses, and profit
            if statement["Type"] == "Income":
                revenue["total"] += statement["Total_Price"]
                if statement["Payment_Method"] not in revenue:
                    revenue[statement["Payment_Method"]] = 0
                revenue[statement["Payment_Method"]] += statement["Total_Price"]
                n_accounts_sold += statement["Quantity"]
            elif statement["Type"] == "Expense":
                expenses["total"] += statement["Total_Price"]
                if statement["Payment_Method"] not in expenses:
                    expenses[statement["Payment_Method"]] = 0
                expenses[statement["Payment_Method"]] += statement["Total_Price"]
        for key in revenue:
            profit[key] = revenue[key] - expenses[key] if key in expenses else revenue[key]
        profit_margin = round(((profit["total"] / expenses["total"]))*100,2) if expenses["total"] != 0 else 'NaN'

        return revenue, expenses, profit, profit_margin, n_accounts_sold

    # CLIENT METHODS

    def insert_new_client(self, id, join_date, level, account_purchases, replacements, services, legit_check):
        """Inserts a new client into the database"""
        # Client should have the following format:
        # {id, join_date, level, account_purchases, replacements,legit_check}
        # account_purchases should have the following format:
        # {date: datetime, n_accs: int, total_price: float, accounts: []}
        # replacements should have the following format:
        # {date: datetime, n_accs: int, accounts: []}
        # services should have the following format:
        # {date: datetime, service: str, n_accs: int, total_price: float}
        self.clients.insert_one({"client_id":id, "register_date":join_date, "level":level, "account_purchases":account_purchases, "replacements": replacements, "service_purchases": services,"legit_check":legit_check})

    def get_all_clients(self):
        """Returns all clients from the database"""
        return list(self.clients.find({}, {"_id":0}))

    def get_client(self, id):
        """Returns a client from the database"""
        return self.clients.find_one({"client_id":id}, {"_id":0})

    def get_client_account_purchases(self, id):
        """Returns all account_purchases of a client from the database"""
        return self.clients.find_one({"client_id":id}, {"_id":0, "account_purchases":1})["account_purchases"]
    
    def get_client_replacements(self, id):
        """Returns all replacements of a client from the database"""
        return self.clients.find_one({"client_id":id}, {"_id":0, "replacements":1})["replacements"]
    
    def get_client_legit_check(self, id):
        """Returns all legit checks of a client from the database"""
        return self.clients.find_one({"client_id":id}, {"_id":0, "legit_check":1})["legit_check"]
    
    def get_client_number_of_account_purchases(self, id):
        """Returns the number of account_purchases of a client from the database"""
        total = 0
        for purchase in self.get_client_account_purchases(id):
            total += purchase["Number_of_accounts"]
        return total
    
    def get_client_number_of_replacements(self, id):
        """Returns the number of replacements of a client from the database"""
        return len(self.get_client_replacements(id))
    
    def get_client_services(self, id):
        """Returns all services of a client from the database"""
        return self.clients.find_one({"client_id":id}, {"_id":0, "service_purchases":1})["service_purchases"]
    
    def get_client_revenue(self, id):
        """Returns the revenue of a client from the database"""
        revenue = 0
        for purchase in self.get_client_account_purchases(id):
            revenue += purchase["Total_price"]
        for service in self.get_client_services(id):
            revenue += service["Total_price"]
        return revenue
    
    def get_client_revenue_per_type(self, id, purchase_type):
        """Returns the revenue of a client from the database"""
        revenue = 0
        if purchase_type == "account_purchase":
            for purchase in self.get_client_account_purchases(id):
                revenue += purchase["Total_price"]
        elif purchase_type == "service":
            for service in self.get_client_services(id):
                revenue += service["Total_price"]
        return revenue
    
    def get_client_level(self, id):
        """Returns the level of a client from the database"""
        return self.clients.find_one({"client_id":id}, {"_id":0, "level":1})["level"]
    
    def add_new_client_purchase(self, id, purchase):
        """Appends a new purchase to a client"""
        self.clients.update_one({"client_id":id}, {"$push": {"account_purchases":purchase}})

    def add_new_client_replacement(self, id, replacement):
        """Appends a new replacement to a client"""
        self.clients.update_one({"client_id":id}, {"$push": {"replacements":replacement}})

    def add_new_client_legit_check(self, id, legit_check):
        """Increments the legit check of a client"""
        self.clients.update_one({"client_id":id}, {"$inc": {"legit_check":legit_check}})
    
    def increment_client_level(self, id, level):
        """Increment the level of a client"""
        self.clients.update_one({"client_id":id}, {"$inc": {"level":level}})

    def get_client_with_most_revenue(self):
        """Returns the client with the most revenue"""
        max_revenue = 0
        max_client = None
        for client in self.get_all_clients():
            revenue = self.get_client_revenue(client["client_id"])
            if revenue > max_revenue:
                max_revenue = revenue
                max_client = client
        return max_client
    

    # TICKET METHODS

    def insert_new_ticket(self, user_id, channel_id):
        """Inserts a new ticket into the database"""
        # Check if the ticket already exists
        if self.get_ticket_by_user_id(user_id) == []:
            self.tickets.insert_one({"user_id":user_id, "channel_id": channel_id, "date":datetime.now()})
        return self.get_ticket_by_user_id(user_id)
    
    def get_all_tickets(self):
        """Returns all tickets from the database"""
        return self.tickets.find({}, {"_id":0})

    def get_ticket_by_user_id(self, user_id):
        """Returns all tickets from a user from the database"""
        return list(self.tickets.find({"user_id":user_id}, {"_id":0}))
    
    def get_ticket_by_channel_id(self, channel_id):
        """Returns all tickets from a channel from the database"""
        return list(self.tickets.find({"channel_id":channel_id}, {"_id":0}))

    def delete_ticket_by_user_id(self, user_id):
        """Deletes a ticket from the database"""
        self.tickets.delete_one({"user_id":user_id})

    def delete_ticket_by_channel_id(self, channel_id):
        """Deletes a ticket from the database"""
        self.tickets.delete_one({"channel_id":channel_id})

    # ORDER METHODS

    def create_new_checkout_session(self, user_id, n_accounts, payment_method=None, coin=None, network=None, txid=None):
        """Creates a new checkout session"""
        # Checkout session should have the following format:
        # {user_id: int, n_accounts: int, total_price: float, coin: str, network: str, txid: str, createdAt: datetime, status: str}

        self.checkout_sessions.insert_one({"user_id":user_id, "n_accounts":n_accounts, "total_price":round(self.get_n_accounts_price(n_accounts)*n_accounts,2), "payment_method": payment_method, "coin":coin, "network":network, "txid":txid, "createdAt":datetime.now(), "status":"pending"})

    def get_pending_checkout_session_by_user_id(self, user_id):
        """Returns a pending checkout session from a user"""
        return self.checkout_sessions.find_one({"user_id":user_id, "status": "pending"})

    def get_checkout_session_by_id(self, id):
        """Returns a checkout session from the database"""
        return self.checkout_sessions.find_one({"_id":ObjectId(id)})
    
    def set_session_status(self, id, status):
        """Sets the status of a checkout session"""
        self.checkout_sessions.update_one({"_id":ObjectId(id)}, {"$set": {"status": status}})
    
    def set_session_txid(self, id, txid):
        """Sets the txid of a checkout session"""
        self.checkout_sessions.update_one({"_id":ObjectId(id)}, {"$set": {"txid": txid}})

    def set_session_coin(self, id, coin):
        """Sets the coin of a checkout session"""
        self.checkout_sessions.update_one({"_id":ObjectId(id)}, {"$set": {"coin": coin}})

    def set_session_network(self, id, network):
        """Sets the network of a checkout session"""
        self.checkout_sessions.update_one({"_id":ObjectId(id)}, {"$set": {"network": network}})

    def set_session_payment_method(self, id, payment_method):
        """Sets the payment method of a checkout session"""
        self.checkout_sessions.update_one({"_id":ObjectId(id)}, {"$set": {"payment_method": payment_method}})
    
    def delete_checkout_session(self, id):
        """Deletes a checkout session from the database"""
        self.checkout_sessions.delete_one({"_id":ObjectId(id)})

def main():

    test = MongoController()
    print(test.get_client_with_most_revenue())

if __name__ == "__main__":
    main()  
