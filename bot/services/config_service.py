"""
Service for managing bot configuration settings.
"""
import asyncio
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from bot.database.models import BotConfig, SubscriptionTier
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

    @classmethod
    async def create_tier(cls, session: AsyncSession, name: str, duration_days: int, price_usd: float) -> SubscriptionTier:
        try:
            # Check if a tier with the same name already exists
            result = await session.execute(select(SubscriptionTier).filter_by(name=name))
            if result.scalars().first():
                raise ConfigError(f"Subscription tier with name '{name}' already exists.")

            new_tier = SubscriptionTier(
                name=name,
                duration_days=duration_days,
                price_usd=price_usd
            )
            session.add(new_tier)
            await session.commit()
            await session.refresh(new_tier)
            return new_tier
        except SQLAlchemyError as e:
            raise ConfigError(f"Error creating subscription tier: {str(e)}")

    @classmethod
    async def get_all_tiers(cls, session: AsyncSession) -> List[SubscriptionTier]:
        try:
            result = await session.execute(select(SubscriptionTier).filter_by(is_active=True))
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise ConfigError(f"Error retrieving subscription tiers: {str(e)}")

    @classmethod
    async def get_tier_by_id(cls, session: AsyncSession, tier_id: int) -> Optional[SubscriptionTier]:
        try:
            result = await session.execute(select(SubscriptionTier).filter_by(id=tier_id))
            return result.scalars().first()
        except SQLAlchemyError as e:
            raise ConfigError(f"Error retrieving subscription tier: {str(e)}")

    @classmethod
    async def update_tier(cls, session: AsyncSession, tier_id: int, **kwargs) -> Optional[SubscriptionTier]:
        try:
            tier = await cls.get_tier_by_id(session, tier_id)
            if not tier:
                return None

            for key, value in kwargs.items():
                if hasattr(tier, key):
                    setattr(tier, key, value)
                else:
                    raise ConfigError(f"Invalid field for SubscriptionTier: {key}")

            await session.commit()
            await session.refresh(tier)
            return tier
        except SQLAlchemyError as e:
            raise ConfigError(f"Error updating subscription tier: {str(e)}")

    @classmethod
    async def delete_tier(cls, session: AsyncSession, tier_id: int) -> bool:
        try:
            tier = await cls.get_tier_by_id(session, tier_id)
            if not tier:
                return False

            tier.is_active = False
            await session.commit()
            return True
        except SQLAlchemyError as e:
            raise ConfigError(f"Error deleting subscription tier: {str(e)}")