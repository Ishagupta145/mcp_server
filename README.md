MCP Server - Cryptocurrency Market Data API

This project is a high-performance Python server that provides a clean, robust API for fetching real-time and historical cryptocurrency market data from major exchanges.

It is built with FastAPI for the async web server and CCXT for unifying API access to hundreds of cryptocurrency exchanges.

Core Features

Real-Time Data: Get the latest ticker price and volume.

Historical Data: Fetch OHLCV (candlestick) data with custom timeframes, start times, and limits.

Caching: Real-time data is cached (default 60s) to reduce API spam and improve response times.

Async First: Built entirely with async/await for high-concurrency I/O operations.

Robust Error Handling: Returns clean JSON error messages for bad symbols, exchange errors, or network issues.

Data Validation: Uses Pydantic models for request and response validation.

Extensively Tested: Includes a full suite of unit and integration tests using pytest.

Setup and Running

1. Prerequisites

Python 3.10+

git

2. Local Setup

Clone the repository:

git clone [https://github.com/Ishagupta145/mcp_server.git](https://github.com/Ishagupta145/mcp_server.git)
cd mcp_server


Create and activate a virtual environment:

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
.\venv\Scripts\activate


Install the required packages:

pip install -r requirements.txt


3. Running the Server

You can run the server directly using uvicorn, which will automatically reload on code changes.

uvicorn src.mcp_server.main:app --reload


The server will be running at http://127.0.0.1:8000.

4. Running Tests

To validate the application and its components, run the test suite using pytest.

pytest


API Endpoints

Once the server is running, you can access the interactive API documentation at:

http://127.0.0.1:8000/docs

1. Get Real-Time Ticker Data

Fetches the latest ticker data. Results are cached for 60 seconds.

GET /ticker/{symbol}

Path Parameters:

symbol (str): The trading pair (e.g., btc-usdt, eth-btc).

Query Parameters:

exchange (str, optional): The exchange ID (e.g., binance, kraken).
Defaults to binance.

Example Request:
GET http://127.0.0.1:8000/ticker/btc-usdt?exchange=coinbasepro

Example Success Response (200):

{
  "symbol": "BTC/USDT",
  "timestamp": 1678886400000,
  "datetime": "2023-03-15T12:00:00.000Z",
  "last": 25000.50,
  "volume": 1204.75
}


Example Error Response (404):

{
  "message": "The symbol 'BAD/SYMBOL' was not found on coinbasepro."
}


2. Get Historical Candlestick Data

Fetches historical OHLCV (candlestick) data.

GET /historical/{symbol}

Path Parameters:

symbol (str): The trading pair (e.g., btc-usdt).

Query Parameters:

timeframe (str, optional): The candle duration. Default: 1h.
(e.g., 1m, 5m, 1h, 1d, 1w).

since (int, optional): The start time as a millisecond Unix timestamp.

limit (int, optional): The number of candles to fetch. Default: 100.

exchange (str, optional): The exchange ID. Default: binance.

Example Request:
GET http://127.0.0.1:8000/historical/eth-usd?timeframe=1d&limit=5&exchange=kraken

Example Success Response (200):

[
  {
    "timestamp": 1678838400000,
    "open": 1650.1,
    "high": 1720.5,
    "low": 1645.0,
    "close": 1715.3,
    "volume": 8500.2
  },
  {
    "timestamp": 1678924800000,
    "open": 1715.3,
    "high": 1740.0,
    "low": 1701.8,
    "close": 1725.0,
    "volume": 7900.0
  }
]


Assumptions & Design Decisions

CCXT vs. CoinMarketCap: I chose CCXT because the request mentioned retrieving data from "major exchanges" (plural). CCXT is a library that interfaces with hundreds of exchanges directly, whereas CoinMarketCap is a single (though comprehensive) data aggregator. CCXT provides more flexibility.

Symbol Normalization: The API assumes symbols will be passed in a friendly format like btc-usdt or ETH-USD. It internally normalizes this to the BTC/USDT format that CCXT requires.

Caching Strategy: Only real-time /ticker data is cached. Historical data is not, as the combinations of timeframe, since, and limit are too numerous for a simple in-memory cache. A more robust solution would use Redis for historical data.

Async Connections: The crypto_service is careful to call await exchange.close() after every API call. This is critical in an async environment to close the underlying httpx session and prevent resource leaks.

Volume: The /ticker endpoint returns baseVolume (e.g., volume in BTC for a BTC/USDT pair) and maps it to the volume field in the response, as this is the most common user expectation.
