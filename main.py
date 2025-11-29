"""
Entry point for the Telegram Admin Bot.

This script assembles all components and provides the execution entry point
for the application optimized for Termux environment.
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from bot.config import Settings
from bot.database.base import engine
from bot.handlers.admin import admin_router
from bot.handlers.user import user_router
from bot.tasks import BackgroundTaskManager
from init_db import init_db


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main function to run the Telegram bot."""
    # Initialize settings
    settings = Settings()

    # Initialize bot with HTML parse mode
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Initialize background task manager
    background_manager = BackgroundTaskManager()

    # Initialize dispatcher
    dp = Dispatcher()

    # Include routers
    dp.include_router(admin_router)
    dp.include_router(user_router)

    # Startup hook
    @dp.startup()
    async def startup_hook():
        logger.info("Bot iniciado...")
        # Ensure database is initialized
        await init_db()
        logger.info("Base de datos inicializada")

        # Start background tasks
        await background_manager.start(bot)

    # Shutdown hook
    @dp.shutdown()
    async def shutdown_hook():
        logger.info("Cerrando bot...")
        # Close bot session first to stop receiving updates
        await bot.session.close()
        await dp.storage.close()
        # Stop background tasks
        await background_manager.stop()
        # Close database connection
        await engine.dispose()
        logger.info("Conexiones cerradas")

    try:
        # Start polling
        logger.info("Iniciando polling...")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Interrupción por teclado detectada. Deteniendo bot...")
    finally:
        # Ensure cleanup happens
        await dp.storage.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())