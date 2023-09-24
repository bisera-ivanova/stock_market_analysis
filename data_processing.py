import requests
import os
import datetime
import time
import sqlite3

from dotenv import load_dotenv

load_dotenv("credentials.env")

#TODO Documentation

STOCKS_LIST = ["TSLA", "AMZN", "INTC", "AAPL", "AVGR", "AMD", "F", "GOOGL", "PLTR", "NVDA", "BAC",
               "RIVN", "PINS", "T", "PFE", "LCID", "META", "MSFT", "BABA", "CSCO"]
STOCK_API_KEY = os.environ.get('STOCK_API_KEY')

# used to track the number of requests being made so that the delay can be optimized
FUNCTION_CALL_COUNTER = 0

# Used to normalize the UNIX timestamp, which is in a Msec format so that it is readable by the time.fromtimestamp()
# function
NORMALIZING_NUMBER = 1000


class DataProcessor:

    def build_request_links(self):
        result = []
        for stock in STOCKS_LIST:
            stock_request_URL = f"https://api.polygon.io/v2/aggs/ticker/{stock}/range/1/week/2022-01-09/2023-01-09?" \
                                f"adjusted=true&sort=asc&limit=120&apiKey={STOCK_API_KEY}"
            result.append(stock_request_URL)
        return result

    def make_requests_for_stock_data(self, stock_link):
        global FUNCTION_CALL_COUNTER
        response = requests.get(stock_link)
        print(response.json())
        if response.json()["resultsCount"]:
            data = self.process_returned_values(response.json())
            self.ingest_values_into_sql(data)
        FUNCTION_CALL_COUNTER += 1
        if FUNCTION_CALL_COUNTER >= 4:
            time.sleep(60)
            FUNCTION_CALL_COUNTER = 0
        if "next_url" in response.json():
            self.make_next_url(response.json())

    def make_next_url(self, response):
        next_url = response["next_url"]
        final_url = f"{next_url}&apiKey={STOCK_API_KEY}"
        self.make_requests_for_stock_data(final_url)

    def process_returned_values(self, response):
        data = {"timestamp": [datetime.datetime.fromtimestamp(result["t"] / NORMALIZING_NUMBER).strftime('%Y-%m-%d %H:%M:%S.%f')
                              for result in response["results"]],
                "stock_name": [response["ticker"]] * response["resultsCount"],
                "highest": [result["h"] for result in response["results"]],
                "lowest": [result["l"] for result in response["results"]],
                "close": [result["c"] for result in response["results"]],
                "open": [result["o"] for result in response["results"]],
                "volume": [result["v"] for result in response["results"]],
                "volume_weighted_average": [result["vw"] for result in response["results"]],
                "number_of_transactions": [result["n"] for result in response["results"]]}
        return data

    def ingest_values_into_sql(self, data):
        conn = sqlite3.connect('stock_data.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_data (
                timestamp TEXT,
                stock_name TEXT,
                highest REAL,
                lowest REAL,
                close REAL,
                open REAL,
                volume REAL,
                volume_weighted_average REAL,
                number_of_transactions INTEGER
            )
        ''')
        for row in zip(data['timestamp'], data['stock_name'], data['highest'], data['lowest'], data['close'],
                       data['open'], data['volume'], data['volume_weighted_average'], data['number_of_transactions']):
            cursor.execute('INSERT INTO stock_data VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', row)

        conn.commit()
        conn.close()


if __name__ == '__main__':
    d = DataProcessor()
    request_links = d.build_request_links()
    for stock in request_links:
        d.make_requests_for_stock_data(stock)
