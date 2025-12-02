"""
Test script to validate the new System A functionality in System B.
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock
from bot.config import Settings
from bot.services.channel_service import ChannelManagementService
from bot.database.models import Channel


async def test_advanced_functionality():
    """Test the new advanced functionality from System A."""
    settings = Settings()

    # Create database engine and session
    engine = create_async_engine(settings.DB_URL)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Create a mock bot instance instead of a real one
    mock_bot = AsyncMock()

    async with async_session() as session:
        print("Testing advanced channel management functionality...")

        # Test 1: List channels (should work even if no channels exist)
        try:
            channels = await ChannelManagementService.list_channels(session)
            print(f"✓ Successfully retrieved {len(channels)} channels")
        except Exception as e:
            print(f"✗ Error listing channels: {e}")

        # Test 2: Get channel stats
        try:
            stats = await ChannelManagementService.get_channel_stats(session, 'vip')
            print(f"✓ Successfully retrieved VIP stats: {stats}")
        except Exception as e:
            print(f"✗ Error getting VIP stats: {e}")

        # Test 3: Get advanced channel stats (new System A functionality)
        try:
            advanced_stats = await ChannelManagementService.get_advanced_channel_stats(session, mock_bot)
            print(f"✓ Successfully retrieved advanced stats: {advanced_stats}")
        except Exception as e:
            print(f"✗ Error getting advanced stats: {e}")

        # Test 4: Configure channel reactions (new System A functionality)
        try:
            result = await ChannelManagementService.configure_channel_reactions(
                session,
                123456789,  # dummy channel ID
                ['👍', '❤️', '🔥']
            )
            print(f"✓ Successfully configured channel reactions: {result}")
        except Exception as e:
            print(f"✗ Error configuring channel reactions: {e}")

        # Test 5: Set content protection (new System A functionality)
        try:
            result = await ChannelManagementService.set_content_protection(
                session,
                123456789,  # dummy channel ID
                True
            )
            print(f"✓ Successfully set content protection: {result}")
        except Exception as e:
            print(f"✗ Error setting content protection: {e}")

    # Close connections
    await engine.dispose()

    print("\nAll tests completed!")


if __name__ == "__main__":
    asyncio.run(test_advanced_functionality())