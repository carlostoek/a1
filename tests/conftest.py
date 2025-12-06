import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from bot.database.base import Base
from bot.database import models  # Import models to register them with Base metadata
from bot.services.dependency_injection import ServiceContainer


@pytest.fixture
def mock_bot():
    """Mock aiogram.Bot object that intercepts send_message and ban_chat_member calls."""
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    bot.ban_chat_member = AsyncMock()
    return bot


@pytest_asyncio.fixture
async def db_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session_factory = sessionmaker(
        engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    # Create and yield a session
    async with async_session_factory() as session:
        yield session
    
    # Close engine after test
    await engine.dispose()


@pytest_asyncio.fixture
async def services(mock_bot, db_session):
    """Create a ServiceContainer with mock bot and test database session."""
    # Create a mock session maker that returns our test session
    async def session_maker():
        return db_session
    
    # Create service container with mocked dependencies
    container = ServiceContainer(bot=mock_bot)
    
    # Override the gamification service to use our test session
    from bot.services.gamification_service import GamificationService
    from bot.services.event_bus import EventBus
    from bot.services.notification_service import NotificationService
    from bot.services.subscription_service import SubscriptionService
    
    # Create test instances with our mocks
    event_bus = EventBus()
    notification_service = NotificationService(bot=mock_bot)
    subscription_service = SubscriptionService()
    
    # Create a new gamification service with test dependencies
    gamification_service = GamificationService(
        session_maker=session_maker,
        event_bus=event_bus,
        notification_service=notification_service,
        subscription_service=subscription_service,
        bot=mock_bot
    )
    
    # Replace the gamification service in the container
    container._gamification_service = gamification_service
    
    return container