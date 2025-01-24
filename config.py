from pydantic_settings import BaseSettings
from typing import List
import os
from functools import lru_cache

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Reddit Ranger"
    
    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:5000",
        "http://localhost:5001",
        "https://reddit-ranger.repl.co"  # Add your Replit domain
    ]
    
    # Reddit API Settings
    REDDIT_CLIENT_ID: str
    REDDIT_CLIENT_SECRET: str
    
    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 5001
    
    class Config:
        case_sensitive = True
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
