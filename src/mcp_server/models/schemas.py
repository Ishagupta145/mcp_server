from pydantic import BaseModel
from typing import List


class TickerResponse(BaseModel):
    """
    Response model for a single ticker's real-time data.
    """
    symbol: str
    timestamp: int
    datetime: str
    last: float
    volume: float


class OHLCVResponse(BaseModel):
    """
    Response model for a single OHLCV (candlestick) data point.
    """
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    class Config:
        """
        Pydantic model configuration.
        """
        # Allows creating the model from a list, e.g., [timestamp, o, h, l, c, v]
        # This is commented out as we will map it manually in the endpoint.
        # In Pydantic v2, this would be:
        # from_attributes = True
        
        # This 'pass' statement fixes the IndentationError.
        pass
