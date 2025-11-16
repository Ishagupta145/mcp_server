from fastapi import FastAPI, Query, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from typing import List
from .services import crypto_service
from .models.schemas import TickerResponse, OHLCVResponse
from .core.exceptions import DataFetchError, InvalidSymbolError, ExchangeError
from .core.config import Settings, get_settings
import uvicorn

# Initialize the FastAPI app
app = FastAPI(
    title="MCP Server - Cryptocurrency Market Data",
    description="A server to fetch real-time and historical crypto data from exchanges using CCXT.",
    version="1.0.0"
)

# --- Exception Handlers ---
# These handlers catch custom exceptions and return friendly JSON responses.

@app.exception_handler(InvalidSymbolError)
async def invalid_symbol_handler(request: Request, exc: InvalidSymbolError):
    return JSONResponse(
        status_code=404,
        content={"message": str(exc)}
    )

@app.exception_handler(ExchangeError)
async def exchange_error_handler(request: Request, exc: ExchangeError):
    # 502 Bad Gateway is appropriate as we are a gateway to another service
    return JSONResponse(
        status_code=502,
        content={"message": f"Error communicating with the exchange: {exc}"}
    )

@app.exception_handler(DataFetchError)
async def data_fetch_handler(request: Request, exc: DataFetchError):
    return JSONResponse(
        status_code=500,
        content={"message": f"An internal error occurred: {exc}"}
    )

# --- Utility Function ---

def normalize_symbol(symbol: str) -> str:
    """
    Converts common input formats (e.g., 'btc-usdt', 'BTC-USD')
    into the 'BTC/USDT' format required by CCXT.
    """
    return symbol.upper().replace('-', '/')

# --- API Endpoints ---

@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Welcome to the MCP Server. See /docs for API documentation."}


@app.get(
    "/ticker/{symbol}",
    response_model=TickerResponse,
    summary="Get Real-Time Ticker Data"
)
async def get_ticker(
    symbol: str,
    exchange: str = Query(
        None,
        description="The ID of the exchange (e.g., 'binance', 'coinbasepro')."
    ),
    settings: Settings = Depends(get_settings)
):
    """
    Fetches the latest real-time ticker data (price, volume, etc.)
    for a given trading pair.
    
    - **symbol**: The trading pair, e.g., `btc-usdt` or `eth-usd`.
    - **exchange**: (Optional) The exchange to query. Defaults to 'binance'.
    
    Results are cached for 1 minute.
    """
    norm_symbol = normalize_symbol(symbol)
    exchange_id = exchange or settings.DEFAULT_EXCHANGE
    
    data = await crypto_service.get_realtime_data(norm_symbol, exchange_id)
    
    # Map the full CCXT response to our clean TickerResponse model
    return TickerResponse(
        symbol=data['symbol'],
        timestamp=data['timestamp'],
        datetime=data['datetime'],
        last=data['last'],
        volume=data['baseVolume']  # 'baseVolume' is usually what people mean by 'volume'
    )


@app.get(
    "/historical/{symbol}",
    response_model=List[OHLCVResponse],
    summary="Get Historical Candlestick Data"
)
async def get_historical(
    symbol: str,
    timeframe: str = Query(
        '1h',
        description="The candlestick duration, e.g., '1m', '5m', '1h', '1d'."
    ),
    since: int = Query(
        None,
        description="Start timestamp in **milliseconds** (e.g., 1678886400000)."
    ),
    limit: int = Query(
        100,
        description="Number of candlesticks to retrieve.",
        le=1000  # Set a reasonable upper limit
    ),
    exchange: str = Query(
        None,
        description="The ID of the exchange (e.g., 'binance', 'kraken')."
    ),
    settings: Settings = Depends(get_settings)
):
    """
    Fetches historical OHLCV (Open, High, Low, Close, Volume) data
    for a given trading pair.
    
    - **symbol**: The trading pair, e.g., `btc-usdt`.
    - **timeframe**: The candle duration ('1m', '1h', '1d', etc.).
    - **since**: (Optional) Start time as a **millisecond** Unix timestamp.
    - **limit**: (Optional) Number of candles to fetch. Default is 100.
    - **exchange**: (Optional) The exchange to query. Defaults to 'binance'.
    """
    norm_symbol = normalize_symbol(symbol)
    exchange_id = exchange or settings.DEFAULT_EXCHANGE

    data = await crypto_service.get_historical_data(
        norm_symbol, timeframe, since, limit, exchange_id
    )
    
    # Map the list of lists from CCXT to our response model
    return [
        OHLCVResponse(
            timestamp=d[0],
            open=d[1],
            high=d[2],
            low=d[3],
            close=d[4],
            volume=d[5]
        ) for d in data
    ]

# This allows running the file directly for development:
# `python -m src.mcp_server.main`
if __name__ == "__main__":
    uvicorn.run("src.mcp_server.main:app", host="0.0.0.0", port=8000, reload=True)