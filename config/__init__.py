"""Configuration package for Reddit Mentat Detector."""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    """Application settings."""
    PROJECT_NAME: str = "Reddit Mentat Detector"
    VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 5002
    LOG_LEVEL: str = "INFO"

    # Authentication settings
    ENABLE_AUTH: bool = os.getenv("ENABLE_AUTH", "false").lower() == "true"
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")

    # Reddit API settings
    REDDIT_CLIENT_ID: str = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    REDDIT_OAUTH_REDIRECT_URI: str = os.getenv("REDDIT_OAUTH_REDIRECT_URI", "http://localhost:5000/oauth/reddit/callback")

    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:5000",
        "http://0.0.0.0:5000",
        "https://*.repl.co"
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()