from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    API_ENV: str = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"
    ]

    # Supabase credentials
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # GenAI (Google Gemini)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # NewsAPI
    NEWS_API_KEY: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

