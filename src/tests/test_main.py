import pytest
import pytest_asyncio
from httpx import AsyncClient
from src.mcp_server.main import app
from src.mcp_server.core.config import get_settings, Settings
from unittest.mock import patch, AsyncMock
from src.mcp_server.core.exceptions import InvalidSymbolError, ExchangeError

# --- Mock Data (from SERVICE layer) ---
MOCK_SERVICE_TICKER = {
    'symbol': 'BTC/USDT',
    'timestamp': 1678886400000,
    'datetime': '2023-03-15T12:00:00.000Z',
    'last': 25000.0,
    'baseVolume': 1000.0, # Service layer provides this
}

MOCK_SERVICE_OHLCV = [
    [1678886400000, 25000.0, 25100.0, 24900.0, 25050.0, 100.0]
]

# --- Fixtures ---

@pytest_asyncio.fixture
async def client():
    """Async test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest_asyncio.fixture
def mock_crypto_service():
    """Patches the crypto_service module used by main.py."""
    with patch('src.mcp_server.main.crypto_service', autospec=True) as mock_service:
        mock_service.get_realtime_data = AsyncMock(return_value=MOCK_SERVICE_TICKER)
        mock_service.get_historical_data = AsyncMock(return_value=MOCK_SERVICE_OHLCV)
        yield mock_service

# --- Test Cases ---

pytestmark = pytest.mark.asyncio

async def test_get_ticker_success(client, mock_crypto_service):
    response = await client.get("/ticker/btc-usdt?exchange=binance")
    
    assert response.status_code == 200
    json_data = response.json()
    
    # Test that the endpoint correctly maps the service data
    assert json_data['symbol'] == 'BTC/USDT'
    assert json_data['last'] == 25000.0
    assert json_data['volume'] == 1000.0 # Check mapping of 'baseVolume' to 'volume'
    
    # Test that the service was called correctly
    mock_crypto_service.get_realtime_data.assert_called_once_with('BTC/USDT', 'binance')

async def test_get_ticker_default_exchange(client, mock_crypto_service):
    # Don't provide 'exchange' query param
    response = await client.get("/ticker/btc-usdt")
    
    assert response.status_code == 200
    
    # Get settings to check the default
    default_exchange = get_settings().DEFAULT_EXCHANGE
    
    # Test that the service was called with the default exchange
    mock_crypto_service.get_realtime_data.assert_called_once_with('BTC/USDT', default_exchange)

async def test_get_ticker_not_found(client, mock_crypto_service):
    # Configure the mock service to raise the "not found" exception
    mock_crypto_service.get_realtime_data.side_effect = InvalidSymbolError("Symbol not found")
    
    response = await client.get("/ticker/bad-symbol")
    
    assert response.status_code == 404
    assert response.json() == {"message": "Symbol not found"}

async def test_get_ticker_exchange_error(client, mock_crypto_service):
    # Configure the mock service to raise an exchange error
    mock_crypto_service.get_realtime_data.side_effect = ExchangeError("Exchange is down")
    
    response = await client.get("/ticker/btc-usdt")
    
    assert response.status_code == 502 # Bad Gateway
    assert response.json() == {"message": "Error communicating with the exchange: Exchange is down"}

async def test_get_historical_success(client, mock_crypto_service):
    response = await client.get("/historical/eth-usdt?timeframe=1d&since=12345&limit=50&exchange=kraken")
    
    assert response.status_code == 200
    json_data = response.json()
    
    # Test that the endpoint correctly maps the service data
    assert len(json_data) == 1
    assert json_data[0]['timestamp'] == 1678886400000
    assert json_data[0]['open'] == 25000.0
    
    # Test that the service was called with all parameters
    mock_crypto_service.get_historical_data.assert_called_once_with(
        'ETH/USDT', '1d', 12345, 50, 'kraken'
    )

async def test_get_historical_defaults(client, mock_crypto_service):
    response = await client.get("/historical/eth-usdt")
    
    assert response.status_code == 200
    
    default_exchange = get_settings().DEFAULT_EXCHANGE
    
    # Test that the service was called with default parameters
    mock_crypto_service.get_historical_data.assert_called_once_with(
        'ETH/USDT',
        '1h',    # default timeframe
        None,    # default since
        100,     # default limit
        default_exchange
    )