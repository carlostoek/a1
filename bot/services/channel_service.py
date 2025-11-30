"""
Service for managing channel requests and statistics.
"""
import logging
from typing import List, Dict, Any, Union
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from aiogram.exceptions import TelegramBadRequest
from bot.database.models import FreeChannelRequest, UserSubscription, BotConfig
from bot.services.exceptions import ServiceError
from bot.services.config_service import ConfigService


class ChannelManagementService:
    """
    Service for managing free channel requests and related statistics.
    """
    
    @staticmethod
    async def register_free_request(session: AsyncSession, user_id: int) -> FreeChannelRequest:
        """
        Register a new free channel request.
        """
        try:
            # Create the request
            request = FreeChannelRequest(
                user_id=user_id,
                request_date=datetime.now(timezone.utc)
            )

            session.add(request)
            await session.commit()
            await session.refresh(request)

            return request
        except SQLAlchemyError as e:
            await session.rollback()
            raise ServiceError(f"Error registering free channel request: {str(e)}")
    
    @staticmethod
    async def get_pending_requests(session: AsyncSession) -> List[FreeChannelRequest]:
        """
        Retrieve all pending (not processed) free channel requests.
        """
        try:
            # Query for requests that haven't been processed
            result = await session.execute(
                select(FreeChannelRequest).where(
                    FreeChannelRequest.processed.is_(False)
                )
            )
            requests = result.scalars().all()

            return requests
        except SQLAlchemyError as e:
            raise ServiceError(f"Error retrieving pending requests: {str(e)}")
    
    @staticmethod
    async def get_channel_stats(session: AsyncSession, channel_type: str) -> dict:
        """
        Get statistics for a specific channel type.

        Args:
            session: Database session
            channel_type: 'vip' or other types

        Returns:
            Dictionary with statistics
        """
        try:
            if channel_type == 'vip':
                # Count active VIP subscribers
                result = await session.execute(
                    select(func.count(UserSubscription.id)).where(
                        UserSubscription.status == "active",
                        UserSubscription.role == "vip",
                        UserSubscription.expiry_date > datetime.now(timezone.utc)
                    )
                )
                active_subscribers = result.scalar()

                return {
                    "active_subscribers": active_subscribers or 0
                }
            else:
                # For other types of channels, return general stats if needed
                result = await session.execute(select(func.count(FreeChannelRequest.id)))
                total_requests = result.scalar()

                result = await session.execute(
                    select(func.count(FreeChannelRequest.id)).where(
                        FreeChannelRequest.processed.is_(False)
                    )
                )
                pending_requests = result.scalar()

                return {
                    "total_requests": total_requests or 0,
                    "pending_requests": pending_requests or 0
                }
        except SQLAlchemyError as e:
            raise ServiceError(f"Error retrieving channel statistics: {str(e)}")

    @staticmethod
    async def register_channel_id(channel_type: str, raw_id: Union[int, str], bot, session: AsyncSession) -> Dict[str, Any]:
        """
        Register channel ID for VIP or Free channel.

        Args:
            channel_type: 'vip' or 'free'
            raw_id: The channel ID (numeric) or username/URL (string)
            bot: Bot instance for verification
            session: Database session

        Returns:
            Dictionary with success status and message
        """
        try:
            # Validate channel type
            if channel_type not in ['vip', 'free']:
                return {"success": False, "error": "Invalid channel type. Use 'vip' or 'free'."}

            # Convert raw_id to integer if it's a numeric string
            channel_id = None
            if isinstance(raw_id, int):
                channel_id = raw_id
            else:
                # Try to extract ID from raw_id that might be username, URL, etc.
                try:
                    # If it's already a numeric ID as string
                    channel_id = int(raw_id)
                except ValueError:
                    # If it's a username or URL, we might need to handle that differently
                    # For now, we'll try to handle common URL formats or @usernames
                    if raw_id.startswith('@'):
                        # It's a username, we need to get the actual ID
                        # This is complex because we need to get the chat by username
                        # For now, we'll return an error suggesting the numeric ID
                        return {"success": False, "error": "Please provide the numeric ID of the channel (e.g., -10012345678) instead of a username."}
                    elif 't.me/' in raw_id or 'telegram.me/' in raw_id:
                        # It's a link to a chat, extracting the ID is not straightforward
                        return {"success": False, "error": "Please provide the numeric ID of the channel (e.g., -10012345678) instead of a link."}
                    else:
                        return {"success": False, "error": "Invalid channel ID format. Please provide the numeric ID (e.g., -10012345678)."}

            # Verify that the bot is an admin in the channel
            try:
                member = await bot.get_chat_member(chat_id=channel_id, user_id=bot.id)
                if not member.status in ['administrator', 'creator']:
                    return {"success": False, "error": "El bot no es administrador o el canal no existe."}
            except TelegramBadRequest:
                return {"success": False, "error": "El bot no es administrador, el canal no existe o el ID es incorrecto."}
            except Exception as e:
                logging.error(f"Error inesperado al verificar el canal {channel_id}: {e}")
                return {"success": False, "error": f"Error inesperado: {e}"}

            # Update the bot configuration with the new channel ID
            config = await ConfigService.get_bot_config(session)
            if channel_type == 'vip':
                config.vip_channel_id = str(channel_id)
            elif channel_type == 'free':
                config.free_channel_id = str(channel_id)

            await session.commit()

            return {"success": True, "channel_id": channel_id}
        except SQLAlchemyError as e:
            await session.rollback()
            return {"success": False, "error": f"Database error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Error: {str(e)}"}


    @staticmethod
    async def request_free_access(session: AsyncSession, user_id: int) -> Dict[str, Any]:
        """
        Handle a user's request for free channel access.

        Args:
            session: Database session
            user_id: ID of the user requesting access

        Returns:
            Dictionary with status and wait time information
        """
        try:
            # Get wait time from config first (optimization to avoid duplicate queries)
            config = await ConfigService.get_bot_config(session)
            wait_time_minutes = config.wait_time_minutes

            # Check if user already has a pending request
            result = await session.execute(
                select(FreeChannelRequest).where(
                    FreeChannelRequest.user_id == user_id,
                    FreeChannelRequest.processed.is_(False)
                )
            )
            pending_request = result.scalars().first()

            if pending_request:
                # User already has a pending request, calculate remaining time

                # Calculate how much time has passed since the request
                current_time = datetime.now(timezone.utc)
                time_since_request = (current_time - pending_request.request_date).total_seconds() / 60  # Convert to minutes
                remaining_minutes = max(0, wait_time_minutes - time_since_request)

                return {
                    "status": "already_requested",
                    "remaining_minutes": round(remaining_minutes),
                    "wait_minutes": wait_time_minutes
                }

            # User doesn't have a pending request, create a new one
            new_request = FreeChannelRequest(
                user_id=user_id,
                request_date=datetime.now(timezone.utc)
            )
            session.add(new_request)
            await session.commit()
            await session.refresh(new_request)

            return {
                "status": "queued",
                "wait_minutes": wait_time_minutes
            }
        except SQLAlchemyError as e:
            await session.rollback()
            raise ServiceError(f"Error processing free access request: {str(e)}")