"""
Service for managing bot configuration settings.
"""
import asyncio
from typing import Optional, Dict, Any, List, Union, TypedDict, Literal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from bot.database.models import BotConfig, SubscriptionTier
from bot.services.exceptions import ConfigError


# Type definitions for config service return values
class WaitTimeUpdateSuccess(TypedDict):
    success: Literal[True]
    wait_time_minutes: int


class WaitTimeUpdateError(TypedDict):
    success: Literal[False]
    error: str


WaitTimeUpdateResult = Union[WaitTimeUpdateSuccess, WaitTimeUpdateError]


@classmethod
async def get_reactions_for_channel(cls, session: AsyncSession, channel_type: str) -> List[str]:
    """
    Get reactions list for a specific channel type.

    Args:
        session: Database session
        channel_type: 'vip' or 'free'

    Returns:
        List of reactions for the specified channel type
    """
    config = await cls.get_bot_config(session)
    if channel_type == "vip":
        return config.vip_reactions or []
    elif channel_type == "free":
        return config.free_reactions or []
    return []


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
            # Get the config without using cache to avoid session conflicts
            result = await session.execute(select(BotConfig))
            config = result.scalars().first()

            # If no config exists, create one with defaults
            if config is None:
                config = BotConfig()
                session.add(config)
                await session.commit()
                await session.refresh(config)

            # Update the specified field
            if hasattr(config, field):
                setattr(config, field, value)
            else:
                raise ConfigError(f"Invalid configuration field: {field}")

            # Commit the changes to the database
            await session.commit()

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

    @classmethod
    async def update_wait_time(cls, minutes: Union[int, str], session: AsyncSession) -> WaitTimeUpdateResult:
        """
        Parse, validate, and update the wait time configuration.

        Args:
            minutes: Number of minutes to wait (as int or string)
            session: Database session

        Returns:
            dict: Operation result with success status and saved value
        """
        try:
            # Convert minutes to integer and validate it's positive
            minutes_int = int(minutes)
            if minutes_int < 0:
                return {
                    "success": False,
                    "error": "El tiempo de espera no puede ser negativo. Por favor, introduce un número entero positivo."
                }

            # Get the bot configuration WITHOUT using cache to avoid session conflicts (similar to update_config)
            result = await session.execute(select(BotConfig))
            config = result.scalars().first()

            # If no config exists, create one with defaults
            if config is None:
                config = BotConfig()
                session.add(config)
                await session.commit()
                await session.refresh(config)

            # Update the wait time minutes field
            config.wait_time_minutes = minutes_int

            # Commit the changes to the database
            await session.commit()

            # Update the cached config
            cls._config_cache = config

            return {
                "success": True,
                "wait_time_minutes": minutes_int
            }
        except ValueError:
            return {
                "success": False,
                "error": "Entrada inválida. Por favor, introduce solo un número entero positivo para los minutos."
            }
        except SQLAlchemyError as e:
            await session.rollback()
            return {
                "success": False,
                "error": f"Error guardando el tiempo de espera: {str(e)}"
            }

    @classmethod
    async def setup_reactions(cls, channel_type: str, reactions_str: str, session: AsyncSession) -> List[str]:
        """
        Parse, validate, and store emoji reactions for a specific channel type.

        Args:
            channel_type: 'vip' or 'free'
            reactions_str: String of emojis separated by commas
            session: Database session

        Returns:
            List of saved emojis.

        Raises:
            ValueError: If input is invalid (e.g., too many emojis, invalid channel type).
            ConfigError: On database errors.
        """
        try:
            reactions_list = [e.strip() for e in reactions_str.split(',') if e.strip()]

            if len(reactions_list) > 10:
                raise ValueError("Número máximo de reacciones excedido (máximo 10 emojis).")

            if channel_type not in ['vip', 'free']:
                raise ValueError("Tipo de canal inválido. Use 'vip' o 'free'.")

            config = await cls.get_bot_config(session)

            if channel_type == 'vip':
                config.vip_reactions = reactions_list
            else:  # 'free'
                config.free_reactions = reactions_list

            await session.commit()

            return reactions_list
        except SQLAlchemyError as e:
            await session.rollback()
            raise ConfigError(f"Error guardando reacciones: {str(e)}")