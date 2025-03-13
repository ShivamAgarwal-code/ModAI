from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List
from pydantic import Field


class Settings(BaseSettings):
    BOT_TOKEN: str = Field(..., env="BOT_TOKEN")
    ADMIN_IDS: List[int] = Field(..., env="ADMIN_IDS")
    HUMAN_SIGNER_1_PRIVATE_KEY: str = Field(..., env="HUMAN_SIGNER_1_PRIVATE_KEY")
    SAFE_ADDRESS: str = Field(..., env="SAFE_ADDRESS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"

@lru_cache
def get_settings() -> Settings:
    return Settings()
