from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import sessionmaker
from bot.config import Settings

settings = Settings()

class Base(DeclarativeBase):
    pass

# Create async engine
engine = create_async_engine(
    settings.DB_URL,
    echo=False  # Set to True for SQL query logging
)

# Create async session maker
async_session = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


async def get_session():
    """Async generator to yield database sessions."""
    async with async_session() as session:
        yield session