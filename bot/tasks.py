"""
Background tasks for the Telegram Admin Bot.
Includes periodic tasks like sending free channel links and checking expired VIPs.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import select

from bot.database.base import get_session
from bot.database.models import FreeChannelRequest, UserSubscription, BotConfig
from bot.services.channel_service import ChannelManagementService
from bot.services.config_service import ConfigService
from bot.config import Settings
from bot.utils.sexy_logger import get_logger


logger = get_logger(__name__)


class BackgroundTaskManager:
    """
    Manages background tasks for the bot.
    Includes processing free channel requests and checking expired VIP subscriptions.
    """
    
    def __init__(self):
        self.running = False
        self.tasks = []
        self.settings = Settings()
    
    async def start(self, bot: Bot):
        """
        Starts the background loops.
        """
        if self.running:
            logger.warning("Background tasks are already running.")
            return

        self.running = True
        logger.startup("Starting background tasks...")

        # Create tasks for the background loops
        self.tasks = [
            asyncio.create_task(self.process_free_requests(bot)),
            asyncio.create_task(self.check_expired_vips(bot))
        ]

        logger.success("Background tasks started.")
    
    async def stop(self):
        """
        Stops the background tasks.
        """
        if not self.running:
            return

        self.running = False
        logger.shutdown("Stopping background tasks...")

        # Cancel all running tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.task("Background task cancelled.")

        self.tasks.clear()
        logger.shutdown("Background tasks stopped.")
    
    async def process_free_requests(self, bot: Bot):
        """
        Loop to process free channel requests after wait time.
        Runs every 60 seconds.
        """
        logger.task("Starting process_free_requests loop...")
        
        while self.running:
            try:
                # Get all pending requests that have waited enough time
                async for session in get_session():
                    # Get wait time from config using the service
                    from bot.services.config_service import ConfigService
                    config = await ConfigService.get_bot_config(session)
                    wait_time_minutes = config.wait_time_minutes
                    
                    # Find requests that have waited enough time
                    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=wait_time_minutes)
                    
                    pending_requests_result = await session.execute(
                        select(FreeChannelRequest).where(
                            FreeChannelRequest.processed.is_(False),
                            FreeChannelRequest.request_date <= cutoff_time
                        )
                    )
                    pending_requests = pending_requests_result.scalars().all()
                    
                    # Process each eligible request
                    for request in pending_requests:
                        try:
                            # Get the free channel ID from database configuration
                            config = await ConfigService.get_bot_config(session)
                            free_channel_id = config.free_channel_id

                            if free_channel_id:
                                try:
                                    # For free channel access, just send the welcome message
                                    # Users will already have access to the channel after admin approval
                                    welcome_text = "🎉 ¡Bienvenido al canal gratuito!"
                                    await bot.send_message(
                                        chat_id=request.user_id,
                                        text=welcome_text
                                    )

                                    # Mark as processed
                                    request.processed = True
                                    request.processed_at = datetime.now(timezone.utc)
                                    await session.commit()

                                    logger.user(f"Sent welcome message to user {request.user_id}")
                                except Exception as e:
                                    # If user blocked the bot or other error, mark as processed anyway
                                    # to avoid retrying forever
                                    logger.error(f"Could not send welcome message to user {request.user_id}: {e}")

                                    # Mark as processed to avoid retrying
                                    request.processed = True
                                    request.processed_at = datetime.now(timezone.utc)
                                    await session.commit()
                            else:
                                logger.warning("Free channel ID not configured")
                                # Mark as processed to avoid retrying
                                request.processed = True
                                request.processed_at = datetime.now(timezone.utc)
                                await session.commit()
                        
                        except Exception as e:
                            logger.error(f"Error processing free request for user {request.user_id}: {e}")
                            # Still want to continue processing other requests
                            await session.rollback()
            
            except Exception as e:
                logger.error(f"Error in process_free_requests loop: {e}")
            
            # Wait 60 seconds before next iteration
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                logger.info("process_free_requests loop cancelled.")
                break
        
        logger.info("process_free_requests loop stopped.")
    
    async def check_expired_vips(self, bot: Bot):
        """
        Loop to check for expired VIP subscriptions and send reminders.
        Runs every 60 minutes.
        """
        logger.task("Starting check_expired_vips loop...")
        
        while self.running:
            try:
                async for session in get_session():
                    now = datetime.now(timezone.utc)

                    # 1. Handle expired subscriptions
                    expired_subs_result = await session.execute(
                        select(UserSubscription).where(
                            UserSubscription.status == "active",
                            UserSubscription.role == "vip",
                            UserSubscription.expiry_date < now
                        )
                    )
                    expired_subs = expired_subs_result.scalars().all()

                    for sub in expired_subs:
                        try:
                            sub.status = "expired"
                            sub.role = "free"
                            
                            config = await ConfigService.get_bot_config(session)
                            vip_channel_id = config.vip_channel_id

                            if vip_channel_id:
                                try:
                                    await bot.ban_chat_member(chat_id=vip_channel_id, user_id=sub.user_id)
                                    await bot.unban_chat_member(chat_id=vip_channel_id, user_id=sub.user_id)
                                    logger.info(f"Removed expired user {sub.user_id} from VIP channel.")
                                except Exception as e:
                                    logger.error(f"Could not remove user {sub.user_id} from VIP channel: {e}")
                            
                            try:
                                await bot.send_message(
                                    chat_id=sub.user_id,
                                    text="🚫 Tu suscripción VIP ha expirado. Tu rol ha sido cambiado a 'free'."
                                )
                            except Exception as e:
                                logger.error(f"Could not notify user {sub.user_id} about expiration: {e}")
                            
                            await session.commit()
                            logger.info(f"Subscription for user {sub.user_id} expired. Role set to 'free'.")

                        except Exception as e:
                            logger.error(f"Error processing expired subscription for user {sub.user_id}: {e}")
                            await session.rollback()

                    # 2. Handle subscription reminders (24 hours before)
                    reminder_time_start = now
                    reminder_time_end = now + timedelta(hours=24)
                    
                    reminder_subs_result = await session.execute(
                        select(UserSubscription).where(
                            UserSubscription.status == "active",
                            UserSubscription.role == "vip",
                            UserSubscription.reminder_sent.is_(False),
                            UserSubscription.expiry_date.between(reminder_time_start, reminder_time_end)
                        )
                    )
                    reminder_subs = reminder_subs_result.scalars().all()

                    for sub in reminder_subs:
                        try:
                            await bot.send_message(
                                chat_id=sub.user_id,
                                text="⏳ ¡Atención! Tu suscripción VIP está a punto de expirar en menos de 24 horas."
                            )
                            sub.reminder_sent = True
                            await session.commit()
                            logger.info(f"Sent expiration reminder to user {sub.user_id}.")
                        except Exception as e:
                            logger.error(f"Could not send reminder to user {sub.user_id}: {e}")
            
            except Exception as e:
                logger.error(f"Error in check_expired_vips loop: {e}")
            
            # Wait 60 minutes before next iteration
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                logger.info("check_expired_vips loop cancelled.")
                break
        
        logger.info("check_expired_vips loop stopped.")