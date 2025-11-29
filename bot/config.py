from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import json


class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: Union[str, List[int]] = "[]"
    DB_URL: str = "sqlite+aiosqlite:///bot.db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator('ADMIN_IDS', mode='before')
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            try:
                # Try parsing as JSON array first
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                else:
                    # If it's not a list, try comma-separated
                    return [int(id_str.strip()) for id_str in v.split(',') if id_str.strip()]
            except json.JSONDecodeError:
                # If that fails, try splitting by comma
                return [int(id_str.strip()) for id_str in v.split(',') if id_str.strip()]
        elif isinstance(v, list):
            return v
        else:
            return []

    @property
    def admin_ids_list(self) -> List[int]:
        """Return the parsed admin IDs as a list of integers."""
        if isinstance(self.ADMIN_IDS, list):
            return [int(item) for item in self.ADMIN_IDS]
        else:
            return []