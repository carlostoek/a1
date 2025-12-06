"""
Entry point for the Telegram Admin Bot.

This script assembles all components and provides the execution entry point
for the application optimized for Termux environment.
"""
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from bot.config import Settings
from bot.database.base import engine
from bot.handlers.admin import admin_router
from bot.handlers.user import user_router
from bot.handlers.wizard_handler import router as wizard_router
from bot.tasks import BackgroundTaskManager
from bot.services.notification_service import NotificationService
from bot.services.dependency_injection import ServiceContainer
from bot.utils.sexy_logger import get_logger
from bot.utils.banner import (
    print_banner,
    print_system_info,
    print_features,
    print_startup_complete,
    print_shutdown,
    print_separator
)
from init_db import init_db


logger = get_logger(__name__)


async def main():
    """Main function to run the Telegram bot."""
    # Print banner
    print_banner()
    print_separator()

    # Initialize settings
    logger.startup("Inicializando configuración del bot...")
    settings = Settings()

    # Initialize bot with HTML parse mode
    logger.startup("Creando instancia del bot...")
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Get bot info for banner
    try:
        bot_info = await bot.get_me()
        bot_username = bot_info.username
    except TelegramAPIError as e:
        logger.error(f"No se pudo obtener información del bot: {e}")
        bot_username = "Unknown"

    # Print system info
    print_system_info(bot_username=bot_username, admin_count=len(settings.admin_ids_list))
    print_separator()
    print_features()
    print_separator()

    # Initialize background task manager
    background_manager = BackgroundTaskManager()

    # Initialize Service Container for dependency injection
    service_container = ServiceContainer(bot)

    # Initialize dispatcher with services container
    dp = Dispatcher()
    dp['services'] = service_container

    # Include routers
    dp.include_router(admin_router)
    dp.include_router(user_router)
    dp.include_router(wizard_router)

    # Startup hook
    @dp.startup()
    async def startup_hook():
        logger.startup("Inicializando componentes del bot...")
        # Ensure database is initialized
        logger.database("Inicializando base de datos...")
        await init_db()
        logger.success("Base de datos inicializada correctamente")

        # Start background tasks
        await background_manager.start(bot)

        # Print startup complete message
        print_startup_complete()

    # Shutdown hook
    @dp.shutdown()
    async def shutdown_hook():
        print_separator()
        print_shutdown()
        logger.shutdown("Cerrando bot...")
        # Close bot session first to stop receiving updates
        logger.network("Cerrando sesión del bot...")
        await bot.session.close()
        await dp.storage.close()
        # Stop background tasks
        await background_manager.stop()
        # Close database connection
        logger.database("Cerrando conexiones de base de datos...")
        await engine.dispose()
        logger.success("Todas las conexiones cerradas correctamente")

    try:
        # Start polling
        logger.api("Iniciando polling de Telegram...")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.warning("Interrupción por teclado detectada. Deteniendo bot...")


if __name__ == "__main__":
    asyncio.run(main())