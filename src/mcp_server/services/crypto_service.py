import ccxt.async_support as ccxt  # Use the async version of CCXT
from cachetools import TTLCache
from ..core.config import settings
from ..core.exceptions import InvalidSymbolError, ExchangeError, DataFetchError
import asyncio

# In-memory cache for real-time ticker data.
# maxsize=1024: stores up to 1024 unique items
# ttl=CACHE_TTL_SECONDS: items expire after the configured time (e.g., 60s)
ticker_cache = TTLCache(maxsize=1024, ttl=settings.CACHE_TTL_SECONDS)
cache_lock = asyncio.Lock()


async def get_exchange(exchange_id: str) -> ccxt.Exchange:
    """
    Initializes and returns an async CCXT exchange instance.
    """
    if exchange_id not in ccxt.exchanges:
        raise ExchangeError(f"Exchange '{exchange_id}' is not supported by CCXT.")
    
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class()
    # Note: We will 'close' this instance in the functions that use it.
    return exchange


async def get_realtime_data(symbol: str, exchange_id: str) -> dict:
    """
    Fetches real-time ticker data for a given symbol and exchange.
    Uses an async-aware TTLCache to cache results.
    """
    cache_key = f"{exchange_id}:{symbol}"
    
    # Check cache first (non-blocking)
    cached_data = ticker_cache.get(cache_key)
    if cached_data:
        return cached_data

    # If not in cache, acquire lock to prevent dogpiling
    async with cache_lock:
        # Double-check cache in case another task populated it while waiting for the lock
        cached_data = ticker_cache.get(cache_key)
        if cached_data:
            return cached_data

        # --- Cache miss: Proceed with API call ---
        exchange = await get_exchange(exchange_id)
        try:
            # Load markets if not already loaded (good practice)
            await exchange.load_markets()
            
            ticker_data = await exchange.fetch_ticker(symbol)
            
            # Store in cache
            ticker_cache[cache_key] = ticker_data
            return ticker_data

        except ccxt.BadSymbol:
            raise InvalidSymbolError(f"The symbol '{symbol}' was not found on {exchange_id}.")
        except ccxt.NetworkError as e:
            raise ExchangeError(f"A network error occurred: {e}")
        except ccxt.ExchangeError as e:
            raise ExchangeError(f"An exchange error occurred: {e}")
        except Exception as e:
            # Catch any other unexpected errors
            raise DataFetchError(f"An unexpected error occurred: {e}")
        finally:
            # CRITICAL: Always close the connection to free up resources
            await exchange.close()


async def get_historical_data(symbol: str, timeframe: str, since: int | None, limit: int, exchange_id: str) -> list:
    """
    Fetches historical OHLCV (candlestick) data.
    
    Note: Historical data is generally not cached at this layer,
    as 'since' and 'limit' params make caching complex.
    A dedicated Redis/DB cache would be better for this.
    """
    exchange = await get_exchange(exchange_id)
    try:
        # Check if the exchange supports this timeframe
        if timeframe not in exchange.timeframes:
            supported = ", ".join(exchange.timeframes.keys())
            raise DataFetchError(f"Timeframe '{timeframe}' not supported by {exchange_id}. Supported: {supported}")

        # Fetch the data
        # CCXT expects 'since' to be a millisecond timestamp
        ohlcv_data = await exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
        
        if not ohlcv_data and since is None:
            # If no data is returned, check if the symbol is valid
            # to distinguish "no data" from "bad symbol".
            await exchange.load_markets()
            if symbol not in exchange.markets:
                 raise InvalidSymbolError(f"The symbol '{symbol}' was not found on {exchange_id}.")
        
        return ohlcv_data

    except ccxt.BadSymbol:
        raise InvalidSymbolError(f"The symbol '{symbol}' was not found on {exchange_id}.")
    except ccxt.NetworkError as e:
        raise ExchangeError(f"A network error occurred: {e}")
    except ccxt.ExchangeError as e:
        raise ExchangeError(f"An exchange error occurred: {e}")
    except Exception as e:
        raise DataFetchError(f"An unexpected error occurred: {e}")
    finally:
        # CRITICAL: Close the connection
        await exchange.close()