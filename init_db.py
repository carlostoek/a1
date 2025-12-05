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
        # Check if the gamification_profiles table has the last_daily_claim column
        try:
            # Check if last_daily_claim column exists in gamification_profiles table
            result = await conn.execute(text(
                "PRAGMA table_info(gamification_profiles);"
            ))
            columns = [row[1] for row in result.fetchall()]  # Get column names
            has_last_daily_claim = 'last_daily_claim' in columns

            if not has_last_daily_claim:
                # Add the column if it doesn't exist
                await conn.execute(text(
                    "ALTER TABLE gamification_profiles ADD COLUMN last_daily_claim DATETIME"
                ))
                print("Added last_daily_claim column to gamification_profiles table")
        except Exception as e:
            # Alternative approach: try adding the column and catch error if it exists
            try:
                await conn.execute(text(
                    "ALTER TABLE gamification_profiles ADD COLUMN last_daily_claim DATETIME"
                ))
                print("Added last_daily_claim column to gamification_profiles table")
            except Exception:
                print("Column last_daily_claim already exists in gamification_profiles table")

        # Check if the bot_config table has the vip_content_protection column
        try:
            # Check if vip_content_protection column exists in bot_config table
            result = await conn.execute(text(
                "PRAGMA table_info(bot_config);"
            ))
            columns = [row[1] for row in result.fetchall()]  # Get column names
            has_vip_content_protection = 'vip_content_protection' in columns

            if not has_vip_content_protection:
                # Add the column if it doesn't exist
                await conn.execute(text(
                    "ALTER TABLE bot_config ADD COLUMN vip_content_protection BOOLEAN DEFAULT 0"
                ))
                print("Added vip_content_protection column to bot_config table")
        except Exception as e:
            # Alternative approach: try adding the column and catch error if it exists
            try:
                await conn.execute(text(
                    "ALTER TABLE bot_config ADD COLUMN vip_content_protection BOOLEAN DEFAULT 0"
                ))
                print("Added vip_content_protection column to bot_config table")
            except Exception:
                print("Column vip_content_protection already exists in bot_config table")

        # Check if the bot_config table has the free_content_protection column
        try:
            # Check if free_content_protection column exists in bot_config table
            result = await conn.execute(text(
                "PRAGMA table_info(bot_config);"
            ))
            columns = [row[1] for row in result.fetchall()]  # Get column names
            has_free_content_protection = 'free_content_protection' in columns

            if not has_free_content_protection:
                # Add the column if it doesn't exist
                await conn.execute(text(
                    "ALTER TABLE bot_config ADD COLUMN free_content_protection BOOLEAN DEFAULT 0"
                ))
                print("Added free_content_protection column to bot_config table")
        except Exception as e:
            # Alternative approach: try adding the column and catch error if it exists
            try:
                await conn.execute(text(
                    "ALTER TABLE bot_config ADD COLUMN free_content_protection BOOLEAN DEFAULT 0"
                ))
                print("Added free_content_protection column to bot_config table")
            except Exception:
                print("Column free_content_protection already exists in bot_config table")


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