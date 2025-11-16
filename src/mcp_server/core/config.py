from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Configuration settings for the application, loaded from environment variables.
    """
    # Cache settings
    CACHE_TTL_SECONDS: int = 60  # 1 minute default cache for real-time data

    # Default exchange settings
    DEFAULT_EXCHANGE: str = 'binance'

    class Config:
        # This allows loading from a .env file (if you create one)
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached instance of the Settings.
    This is the recommended way to use settings with FastAPI dependencies.
    """
    return Settings()


settings = get_settings()