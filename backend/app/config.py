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

    # Supabase credentials (2026 API Keys & JWKS)
    SUPABASE_URL: str = "https://qrqcjxlexwvvgvisnphx.supabase.co"
    SUPABASE_KEY: str = ""
    SUPABASE_PUBLISHABLE_KEY: str = "sb_publishable_im4IGU7Cwf4VAcQN87H0aA_5KQjoZB5"
    SUPABASE_SECRET_KEY: str = "sb_secret__xJg7qLzP7ZiVIsevVoDoQ_9T9trcAH"
    SUPABASE_JWKS_URL: str = "https://qrqcjxlexwvvgvisnphx.supabase.co/auth/v1/.well-known/jwks.json"

    # GenAI (Google Gemini)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # NewsAPI
    NEWS_API_KEY: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

