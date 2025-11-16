"""
Custom exception classes for the application.
"""


class DataFetchError(Exception):
    """Base exception for data fetching issues."""
    pass


class InvalidSymbolError(DataFetchError):
    """Raised when a symbol is not found on the exchange."""
    pass


class ExchangeError(DataFetchError):
    """Raised for general exchange or network errors."""
    pass