from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str
    APP_ENV: str
    APP_DEBUG: bool
    FRONTEND_URL: List[str]
    JWT_SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    DATABASE_URL: str

    LOGIN_RATE_LIMIT_MAX_REQUESTS: int
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int
    LOGIN_RATE_LIMIT_BLOCK_SECONDS: int

    # Orbit Assistant (Now configured for Groq's Free Llama3 Models)
    XAI_API_KEY: str = ""
    GROK_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROK_MODEL: str = "llama-3.1-8b-instant"
    ASSISTANT_CONFIDENCE_THRESHOLD: float = 0.8
    CHAT_SESSION_TIMEOUT_MINUTES: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"

settings = Settings()