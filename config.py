from pydantic_settings import BaseSettings
from typing import List
import os
from functools import lru_cache
import logging

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Reddit Ranger"
    VERSION: str = "1.0.0"

    # CORS Settings - Updated for production
    CORS_ORIGINS: List[str] = [
        "http://localhost:5000",
        "http://localhost:5001",
        "https://reddit-ranger.repl.co",
        "https://*.repl.co"  # Allow all Replit domains
    ]

    # Reddit API Settings
    REDDIT_CLIENT_ID: str
    REDDIT_CLIENT_SECRET: str

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 5002

    # Logging Settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    class Config:
        case_sensitive = True
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    settings = Settings()

    # Configure logging based on settings
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format=settings.LOG_FORMAT
    )

    return settings