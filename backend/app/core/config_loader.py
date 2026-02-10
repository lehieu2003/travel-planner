# backend/app/core/config_loader.py

import os
from narwhals import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    GOOGLE_MAPS_API_KEY: str
    SERPAPI_KEY: str
    JWT_SECRET_KEY: str = "supersecret"
    gpt_model_nano: str = "gpt-4.1-nano"
    gpt_model_mini: str = "gpt-4.1-mini"
    access_token_expire_minutes: int = 1440
    default_origin_city: str = "SGN"
    environment: str = "development"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()