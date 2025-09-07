# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str  # = DATABASE_URL

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",  # そのまま DATABASE_URL を読む
        extra="ignore",
    )


settings = Settings()
