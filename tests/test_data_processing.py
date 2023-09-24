import unittest
import sqlite3

import stock_market_analysis.data_processing as STA

from unittest.mock import patch


class TestDataProcessing(unittest.TestCase):
    def setUp(self) -> None:
        self.tested_class = STA.DataProcessor()
        STA.STOCKS_LIST = ["TSLA"]
        # mock API Key
        STA.STOCK_API_KEY = "aklhewoiu12y938472039582"

    def test_build_request_links(self):
        result = self.tested_class.build_request_links()
        self.assertEqual(["https://api.polygon.io/v2/aggs/ticker/TSLA/range/1/week/2022-01-09/2023-01-09?"
                          "adjusted=true&sort=asc&limit=120&apiKey=aklhewoiu12y938472039582"], result)

    @patch('stock_market_analysis.data_processing.requests.get')
    @patch('stock_market_analysis.data_processing.DataProcessor.process_returned_values')
    @patch('stock_market_analysis.data_processing.DataProcessor.ingest_values_into_sql')
    def test_make_requests_for_stock_data(self, mock_ingest, mock_process, mock_get):
        mock_response = {
            "results": [
                {"t": 1632423600000},
                {"t": 1633028400000},
            ],
            "resultsCount": 2,
            "ticker": "TSLA"
        }
        mock_get.return_value.json.return_value = mock_response

        self.tested_class.make_requests_for_stock_data("https://api.polygon.io/v2/aggs/ticker/TSLA/range/1/week/"
                                                       "2022-01-09/2023-01-09?adjusted=true&sort=asc&limit=120&"
                                                       "apiKey=aklhewoiu12y938472039582")

        self.assertTrue(mock_get.called)
        self.assertTrue(mock_process.called)
        self.assertTrue(mock_ingest.called)
        self.assertEqual(STA.FUNCTION_CALL_COUNTER, 1)  # Check that the counter was incremented

    @patch('stock_market_analysis.data_processing.DataProcessor.make_requests_for_stock_data')
    def test_make_next_url(self, mock_make_request):
        mock_response = {
            "results": [
                {"t": 1632423600000},
                {"t": 1633028400000},
            ],
            "resultsCount": 2,
            "ticker": "TSLA",
            "next_url": "https://api.polygon.io/v2/aggs/ticker/TSLA/range/1/week/1656820800000/"
                        "2023-01-09?cursor=bGltaXQ9MTIwJnNvcnQ9YXNj"
        }
        self.tested_class.make_next_url(mock_response)
        call_args = mock_make_request.call_args

        # Extract the final_url from the call arguments for the self.make_requests_for_stock_data(final_url)
        # function call
        final_url = call_args[0][0]
        self.assertEqual("https://api.polygon.io/v2/aggs/ticker/TSLA/range/1/week/1656820800000/"
                         "2023-01-09?cursor=bGltaXQ9MTIwJnNvcnQ9YXNj&apiKey=aklhewoiu12y938472039582", final_url)
        self.assertTrue(mock_make_request.called)

    def test_process_returned_values(self):
        mock_response = {
            "ticker": "TSLA",
            "queryCount": 120,
            "resultsCount": 1,
            "adjusted": "true",
            "results": [
                {
                    "v": 4.64466348e+08,
                    "vw": 226.4403,
                    "o": 218.34,
                    "c": 253.21,
                    "h": 253.2667,
                    "l": 206.8567,
                    "t": 1653192000000,
                    "n": 4268178
                },
            ],
            "status": "OK",
            "request_id": "1b5767915d76312b3ce81aac5e4751bd",
            "count": 25,
            "next_url": "https://api.polygon.io/v2/aggs/ticker/TSLA/range/1/week/1656820800000/2023-01-09?cursor=bGltaXQ9MTIwJnNvcnQ9YXNj"
        }
        result = self.tested_class.process_returned_values(mock_response)
        expected_dict = {"timestamp": ["2022-05-22 07:00:00.000000"], "stock_name": ["TSLA"], "highest": [253.2667],
                         "lowest": [206.8567], "close": [253.21], "open": [218.34], "volume": [464466348.0],
                         "volume_weighted_average": [226.4403], "number_of_transactions": [4268178]}
        self.assertEqual(result, expected_dict)

    def test_ingest_into_sql(self):
        conn = sqlite3.connect("stock_data.db")
        cursor = conn.cursor()

        cursor.execute("SELECT 1")
        result = cursor.fetchone()

        cursor.close()
        conn.close()
        # checks whether a connection to the created data file is established
        self.assertEqual((1,), result)

if __name__ == '__main__':
    unittest.main()
