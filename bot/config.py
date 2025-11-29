from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: List[int] = Field(default_factory=list)
    DB_URL: str = "sqlite+aiosqlite:///bot.db"

    class Config:
        env_file = ".env"