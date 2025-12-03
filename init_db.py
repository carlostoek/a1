import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.base import engine, Base, async_session
from bot.database.models import Rank


async def init_db():
    """Initialize the database by creating all tables."""
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    # Initialize rank data after creating tables
    await seed_ranks()
    print("Database tables created successfully!")
    print("Rank data seeded successfully!")


async def seed_ranks():
    """Create default ranks if they don't exist."""
    async with async_session() as session:
        # Check if ranks already exist
        result = await session.execute(
            text("SELECT COUNT(*) FROM gamification_ranks")
        )
        count = result.scalar()

        if count == 0:  # Only add ranks if table is empty
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