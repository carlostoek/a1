import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from bot.database.base import Base
from bot.database import models  # Import models to register them with Base metadata
from bot.services.dependency_injection import ServiceContainer
from bot.services.gamification_service import GamificationService


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
async def base_rank(db_session):
    """Create a base rank for testing."""
    from bot.database.models import Rank
    base_rank = Rank(
        name="Bronze",
        min_points=0,
        reward_description="Base rank"
    )
    db_session.add(base_rank)
    await db_session.commit()
    await db_session.refresh(base_rank)
    return base_rank


@pytest_asyncio.fixture
async def services(mock_bot, db_session):
    """Create a ServiceContainer with mock bot and test database session."""
    # Create a mock session maker that returns our test session
    async def session_maker():
        return db_session

    # Create service container with mocked dependencies
    container = ServiceContainer(bot=mock_bot)

    # Reuse the container's event bus to ensure proper event handling
    event_bus = container.bus
    notification_service = container.notify
    subscription_service = container.subs

    # Create a new gamification service with test dependencies
    gamification_service = GamificationService(
        session_maker=session_maker,
        event_bus=event_bus,
        notification_service=notification_service,
        subscription_service=subscription_service,
        bot=mock_bot
    )

    # Setup listeners for the new gamification service instance
    gamification_service.setup_listeners()

    # Replace the gamification service in the container
    container._gamification_service = gamification_service

    return container