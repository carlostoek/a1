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
from bot.services.config_service import ConfigService


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

        # Test 1: Get channel stats
        try:
            stats = await ChannelManagementService.get_channel_stats(session, 'vip')
            print(f"✓ Successfully retrieved VIP stats: {stats}")
        except Exception as e:
            print(f"✗ Error getting VIP stats: {e}")

        # Test 2: Test content protection toggle
        try:
            result = await ConfigService.toggle_content_protection(session, 'vip', True)
            print(f"✓ Successfully tested content protection: {result}")
        except Exception as e:
            print(f"✗ Error testing content protection: {e}")

        # Test 3: Test cleanup of old requests
        try:
            result = await ChannelManagementService.cleanup_old_requests(session)
            print(f"✓ Successfully tested cleanup of old requests: {result}")
        except Exception as e:
            print(f"✗ Error testing cleanup of old requests: {e}")

    # Close connections
    await engine.dispose()

    print("\nAll tests completed!")


if __name__ == "__main__":
    asyncio.run(test_advanced_functionality())