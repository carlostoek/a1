import asyncio
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.base import engine, Base, async_session
from bot.database.models import BotConfig, GamificationProfile, Rank


async def init_db():
    """Initialize the database by creating all tables."""
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    # Run migrations to add new columns if they don't exist
    await run_migrations()

    # Initialize rank data after creating tables
    await seed_ranks()
    print("Database tables created successfully!")
    print("Rank data seeded successfully!")


async def run_migrations():
    """Run database migrations to handle schema updates."""
    async with engine.begin() as conn:
        # Helper function to add column if it doesn't exist
        async def _add_column_if_not_exists(table_name: str, column_name: str, column_type: str):
            try:
                # Check if column exists in the table
                result = await conn.execute(text(f"PRAGMA table_info({table_name});"))
                columns = [row[1] for row in result.fetchall()]  # Get column names
                if column_name not in columns:
                    # Add the column if it doesn't exist
                    await conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
                    print(f"Added {column_name} column to {table_name} table")
                else:
                    print(f"Column {column_name} already exists in {table_name} table")
            except Exception:
                # Alternative approach: try adding the column and catch error if it exists
                try:
                    await conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
                    print(f"Added {column_name} column to {table_name} table")
                except Exception:
                    print(f"Column {column_name} already exists in {table_name} table")

        # Add columns as needed
        await _add_column_if_not_exists("gamification_profiles", "last_daily_claim", "DATETIME")
        await _add_column_if_not_exists("bot_config", "vip_content_protection", "BOOLEAN DEFAULT 0")
        await _add_column_if_not_exists("bot_config", "free_content_protection", "BOOLEAN DEFAULT 0")


async def seed_ranks():
    """Create default ranks if they don't exist."""
    async with async_session() as session:
        # Check if ranks already exist using SQLAlchemy ORM
        result = await session.execute(
            select(Rank).limit(1)  # Just check if any rank exists, limit 1 for efficiency
        )
        exists = result.first() is not None

        if not exists:  # Only add ranks if table is empty
            ranks_data = [
                {"name": "Bronce", "min_points": 0, "reward_description": "Nivel inicial de bienvenida"},
                {"name": "Plata", "min_points": 100, "reward_description": "Reconocimiento de participación activa"},
                {"name": "Oro", "min_points": 500, "reward_description": "Miembro destacado"},
                {"name": "Platino", "min_points": 1000, "reward_description": "Usuario experto"},
                {"name": "Diamante", "min_points": 5000, "reward_description": "Usuario elite"}
            ]

            for rank_data in ranks_data:
                rank = Rank(**rank_data)
                session.add(rank)

            await session.commit()
            print(f"Seeded {len(ranks_data)} default ranks")


if __name__ == "__main__":
    asyncio.run(init_db())