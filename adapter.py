"""This program will transform data from a csv into mongodb documents"""
# Each line in the csv file has the following format:
# Date,Type,Product,Quantity,Price,PayMethod,ClientID

# Each document will have the following format:
# {
#    Type: 'Income',
#    Product: 'Account',
#    Quantity: 1,
#    Unit_price: 1.5,
#    Total_Price: 1.5,
#    Payment_Method: 'Revolut',
#    Client_id: '945008124748779520',
#    Date: ISODate("2023-02-08T17:55:41.250Z")
#  }

import csv
import datetime
from mongo_controller import MongoController

def main():
    with open('finance.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            # Skip the header
            if row[0] == 'Date':
                continue
            # Create the document
            document = {
                'Type': row[1],
                'Product': row[2],
                'Quantity': float(row[3]),
                'Unit_price': round(float(row[4])/float(row[3]),2),
                'Total_Price': float(row[4]),
                'Payment_Method': row[5],
                'Client_id': str(row[6]),
                'Date': datetime.datetime.strptime(row[0], '%d/%m/%Y')
            }
            # Insert the document
            MongoController().insert_finance_statement(document)

if __name__ == "__main__":
    main()