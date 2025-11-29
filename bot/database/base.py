from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

# Create async engine
engine = create_async_engine(
    "sqlite+aiosqlite:///bot.db",
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