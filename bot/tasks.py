"""
Background tasks for the Telegram Admin Bot.
Includes periodic tasks like sending free channel links and checking expired VIPs.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import select

from bot.database.base import get_session
from bot.database.models import FreeChannelRequest, VIPSubscriber, BotConfig
from bot.services.channel_service import ChannelManagementService
from bot.config import Settings


logger = logging.getLogger(__name__)


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
        logger.info("Starting background tasks...")
        
        # Create tasks for the background loops
        self.tasks = [
            asyncio.create_task(self.process_free_requests(bot)),
            asyncio.create_task(self.check_expired_vips(bot))
        ]
        
        logger.info("Background tasks started.")
    
    async def stop(self):
        """
        Stops the background tasks.
        """
        if not self.running:
            return
        
        self.running = False
        logger.info("Stopping background tasks...")
        
        # Cancel all running tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info("Background task cancelled.")
        
        self.tasks.clear()
        logger.info("Background tasks stopped.")
    
    async def process_free_requests(self, bot: Bot):
        """
        Loop to process free channel requests after wait time.
        Runs every 60 seconds.
        """
        logger.info("Starting process_free_requests loop...")
        
        while self.running:
            try:
                # Get all pending requests that have waited enough time
                async for session in get_session():
                    # Get wait time from config
                    config_result = await session.execute(select(BotConfig))
                    config = config_result.scalars().first()
                    
                    if not config:
                        # Create default config if none exists
                        config = BotConfig(wait_time_minutes=30)  # Default to 30 minutes
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
                            # Generate invite link to the free channel
                            if self.settings.free_channel_id:
                                try:
                                    # Create invite link for the free channel
                                    invite_link = await bot.create_chat_invite_link(
                                        chat_id=self.settings.free_channel_id,
                                        member_limit=1  # Single-use link
                                    )
                                    
                                    # Send the invite link to the user
                                    await bot.send_message(
                                        chat_id=request.user_id,
                                        text=f"✅ ¡Tu espera terminó! Entra aquí: {invite_link.invite_link}"
                                    )
                                    
                                    # Mark as processed
                                    request.processed = True
                                    request.processed_at = datetime.now(timezone.utc)
                                    await session.commit()
                                    
                                    logger.info(f"Sent invite link to user {request.user_id}")
                                except Exception as e:
                                    # If user blocked the bot or other error, mark as processed anyway
                                    # to avoid retrying forever
                                    logger.error(f"Could not send invite to user {request.user_id}: {e}")
                                    
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
        Loop to check for expired VIP subscriptions.
        Runs every 60 minutes.
        """
        logger.info("Starting check_expired_vips loop...")
        
        while self.running:
            try:
                # Get all active users whose subscriptions have expired
                async for session in get_session():
                    current_time = datetime.now(timezone.utc)
                    
                    expired_vips_result = await session.execute(
                        select(VIPSubscriber).where(
                            VIPSubscriber.status == "active",
                            VIPSubscriber.expiry_date < current_time
                        )
                    )
                    expired_vips = expired_vips_result.scalars().all()
                    
                    # Process each expired subscription
                    for subscriber in expired_vips:
                        try:
                            # Update status to expired
                            subscriber.status = "expired"
                            
                            # If there's a VIP channel, remove the user
                            if self.settings.vip_channel_id:
                                try:
                                    # Remove user from VIP channel (ban and unban to kick)
                                    await bot.ban_chat_member(
                                        chat_id=self.settings.vip_channel_id,
                                        user_id=subscriber.user_id
                                    )
                                    await bot.unban_chat_member(
                                        chat_id=self.settings.vip_channel_id,
                                        user_id=subscriber.user_id
                                    )
                                    
                                    logger.info(f"Removed expired VIP user {subscriber.user_id} from channel")
                                except Exception as e:
                                    logger.error(f"Could not remove user {subscriber.user_id} from VIP channel: {e}")
                            
                            # Notify the user about expiration
                            try:
                                await bot.send_message(
                                    chat_id=subscriber.user_id,
                                    text="🚫 Tu suscripción VIP ha expirado."
                                )
                            except Exception as e:
                                logger.error(f"Could not notify user {subscriber.user_id} about expiration: {e}")
                            
                            # Commit changes
                            await session.commit()
                            
                            logger.info(f"Marked VIP subscription expired for user {subscriber.user_id}")
                        except Exception as e:
                            logger.error(f"Error processing expired VIP for user {subscriber.user_id}: {e}")
                            await session.rollback()
            
            except Exception as e:
                logger.error(f"Error in check_expired_vips loop: {e}")
            
            # Wait 60 minutes before next iteration
            try:
                await asyncio.sleep(3600)  # 60 minutes
            except asyncio.CancelledError:
                logger.info("check_expired_vips loop cancelled.")
                break
        
        logger.info("check_expired_vips loop stopped.")