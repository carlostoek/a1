"""
Service for managing bot configuration settings.
"""
import asyncio
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from bot.database.models import BotConfig
from bot.services.exceptions import ConfigError


class ConfigService:
    """
    Service for managing bot configuration settings with in-memory caching.
    """

    _config_cache: Optional[BotConfig] = None
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_bot_config(cls, session: AsyncSession) -> BotConfig:
        """
        Retrieve the bot configuration. If it doesn't exist, create one with defaults.
        Uses in-memory cache to avoid constant queries.
        """
        # Check if config is already cached
        if cls._config_cache is not None:
            return cls._config_cache

        async with cls._lock:
            # Double-check after acquiring lock
            if cls._config_cache is not None:
                return cls._config_cache

            try:
                # Query for existing config
                result = await session.execute(select(BotConfig))
                config = result.scalars().first()

                # If no config exists, create one with defaults
                if config is None:
                    config = BotConfig()
                    session.add(config)
                    await session.commit()
                    await session.refresh(config)

                # Cache the config for subsequent requests
                cls._config_cache = config
                return config
            except SQLAlchemyError as e:
                raise ConfigError(f"Error retrieving bot configuration: {str(e)}")
    
    @classmethod
    async def update_config(cls, session: AsyncSession, field: str, value: Any) -> BotConfig:
        """
        Update a specific configuration field and return the updated config.
        """
        try:
            config = await cls.get_bot_config(session)

            # Update the specified field
            if hasattr(config, field):
                setattr(config, field, value)
            else:
                raise ConfigError(f"Invalid configuration field: {field}")

            # Commit the changes to the database
            await session.commit()
            await session.refresh(config)

            # Update the cached config
            cls._config_cache = config

            return config
        except SQLAlchemyError as e:
            raise ConfigError(f"Error updating bot configuration: {str(e)}")

    @classmethod
    def clear_cache(cls) -> None:
        """
        Clear the in-memory configuration cache.
        """
        cls._config_cache = None