import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.mcp_server.services import crypto_service
from src.mcp_server.core.exceptions import InvalidSymbolError, ExchangeError, DataFetchError
import ccxt.async_support as ccxt  # Import for patching side_effects

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio

# --- Mock Data ---
MOCK_TICKER_DATA = {
    'symbol': 'BTC/USDT',
    'timestamp': 1678886400000,
    'datetime': '2023-03-15T12:00:00.000Z',
    'last': 25000.0,
    'baseVolume': 1000.0,
    # ... other fields
}

MOCK_OHLCV_DATA = [
    [1678886400000, 25000.0, 25100.0, 24900.0, 25050.0, 100.0],
    [1678886760000, 25050.0, 25150.0, 25000.0, 25100.0, 120.0],
]

# --- Fixtures ---

@pytest_asyncio.fixture
def mock_exchange_instance():
    """Mocks a single instance of a CCXT exchange."""
    exchange_mock = AsyncMock(spec=ccxt.Exchange)
    exchange_mock.fetch_ticker = AsyncMock(return_value=MOCK_TICKER_DATA)
    exchange_mock.fetch_ohlcv = AsyncMock(return_value=MOCK_OHLCV_DATA)
    exchange_mock.load_markets = AsyncMock()
    exchange_mock.close = AsyncMock()
    exchange_mock.timeframes = {'1h': '1h', '1d': '1d'} # Mock supported timeframes
    exchange_mock.markets = {'BTC/USDT': {}} # Mock supported markets
    return exchange_mock

@pytest_asyncio.fixture(autouse=True)
def patch_get_exchange(mock_exchange_instance):
    """
    Patches the 'get_exchange' service function to always return
    our mock instance, avoiding all real CCXT initialization.
    """
    # We patch 'get_exchange' within the crypto_service module
    with patch('src.mcp_server.services.crypto_service.get_exchange', 
             return_value=mock_exchange_instance) as mock_get:
        yield mock_get

@pytest_asyncio.fixture(autouse=True)
def clear_ticker_cache():
    """Ensures the ticker cache is clear before each test."""
    crypto_service.ticker_cache.clear()
    yield
    crypto_service.ticker_cache.clear()

# --- Test Cases for get_realtime_data ---

async def test_get_realtime_data_success(mock_exchange_instance):
    data = await crypto_service.get_realtime_data('BTC/USDT', 'binance')
    
    assert data == MOCK_TICKER_DATA
    mock_exchange_instance.fetch_ticker.assert_called_once_with('BTC/USDT')
    mock_exchange_instance.close.assert_called_once()
    # Check that data is now in cache
    assert crypto_service.ticker_cache.get('binance:BTC/USDT') == MOCK_TICKER_DATA

async def test_get_realtime_data_caching(mock_exchange_instance):
    # First call - should hit API and cache
    await crypto_service.get_realtime_data('BTC/USDT', 'binance')
    
    # Second call - should use cache
    data = await crypto_service.get_realtime_data('BTC/USDT', 'binance')
    
    assert data == MOCK_TICKER_DATA
    # fetch_ticker should only have been called ONCE across both calls
    mock_exchange_instance.fetch_ticker.assert_called_once()
    # close should also only be called ONCE
    mock_exchange_instance.close.assert_called_once()

async def test_get_realtime_data_bad_symbol(mock_exchange_instance):
    mock_exchange_instance.fetch_ticker.side_effect = ccxt.BadSymbol("Symbol not found")
    
    with pytest.raises(InvalidSymbolError, match="symbol 'BAD/SYMBOL' was not found"):
        await crypto_service.get_realtime_data('BAD/SYMBOL', 'binance')
    
    mock_exchange_instance.close.assert_called_once()

async def test_get_realtime_data_network_error(mock_exchange_instance):
    mock_exchange_instance.fetch_ticker.side_effect = ccxt.NetworkError("Connection timed out")
    
    with pytest.raises(ExchangeError, match="network error occurred: Connection timed out"):
        await crypto_service.get_realtime_data('BTC/USDT', 'binance')
        
    mock_exchange_instance.close.assert_called_once()

# --- Test Cases for get_historical_data ---

async def test_get_historical_data_success(mock_exchange_instance):
    data = await crypto_service.get_historical_data('BTC/USDT', '1h', None, 100, 'binance')
    
    assert data == MOCK_OHLCV_DATA
    mock_exchange_instance.fetch_ohlcv.assert_called_once_with('BTC/USDT', '1h', since=None, limit=100)
    mock_exchange_instance.close.assert_called_once()

async def test_get_historical_data_bad_symbol(mock_exchange_instance):
    mock_exchange_instance.fetch_ohlcv.side_effect = ccxt.BadSymbol("Symbol not found")
    
    with pytest.raises(InvalidSymbolError, match="symbol 'BAD/SYMBOL' was not found"):
        await crypto_service.get_historical_data('BAD/SYMBOL', '1h', None, 100, 'binance')
        
    mock_exchange_instance.close.assert_called_once()

async def test_get_historical_data_bad_timeframe(mock_exchange_instance):
    with pytest.raises(DataFetchError, match="Timeframe '10y' not supported"):
        await crypto_service.get_historical_data('BTC/USDT', '10y', None, 100, 'binance')
    
    # close should still be called even on failure
    mock_exchange_instance.close.assert_called_once()