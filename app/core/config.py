from pydantic_settings import BaseSettings
from typing import List

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

    # Email (SMTP) Settings
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_SERVER: str
    MAIL_PORT: int
    
    LOGIN_RATE_LIMIT_MAX_REQUESTS: int
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int
    LOGIN_RATE_LIMIT_BLOCK_SECONDS: int
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
settings = Settings()