"""
Service for managing channel requests and statistics.
"""
import logging
from typing import List, Dict, Any, Union, TypedDict, NotRequired
from aiogram import Bot
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from aiogram.exceptions import TelegramBadRequest
from bot.database.models import FreeChannelRequest, UserSubscription, BotConfig
from bot.services.exceptions import ServiceError
from bot.services.config_service import ConfigService
from bot.utils.ui import MenuFactory


# Type definitions for channel service return values
class BroadcastResult(TypedDict):
    success: bool
    message_id: NotRequired[int]
    error: NotRequired[str]


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

    @staticmethod
    async def process_pending_requests(session: AsyncSession, bot: 'Bot') -> Dict[str, Any]:
        """
        Process all pending free channel requests by approving them.

        Args:
            session: Database session
            bot: Bot instance for sending messages

        Returns:
            Dictionary with success status and summary of processed requests
        """
        try:
            # Get all pending requests
            pending_requests = await ChannelManagementService.get_pending_requests(session)

            if not pending_requests:
                return {
                    "success": True,
                    "processed_count": 0,
                    "message": "No pending requests to process"
                }

            processed_count = 0
            errors = []

            for request in pending_requests:
                try:
                    # Approve the individual request
                    result = await ChannelManagementService.approve_request(
                        request_id=request.id,
                        session=session,
                        bot=bot
                    )
                    if result["success"]:
                        processed_count += 1
                    else:
                        errors.append(f"Request {request.id}: {result['error']}")
                except Exception as e:
                    logging.exception(f"Error al procesar la solicitud {request.id}")
                    errors.append(f"Request {request.id}: {str(e)}")

            summary_message = f"Processed {processed_count}/{len(pending_requests)} pending requests"
            if errors:
                summary_message += f"; {len(errors)} errors occurred"

            return {
                "success": True,
                "processed_count": processed_count,
                "errors": errors,
                "message": summary_message
            }
        except Exception as e:
            return {
                "success": False,
                "processed_count": 0,
                "error": f"Error processing pending requests: {str(e)}"
            }

    @staticmethod
    async def approve_request(request_id: int, session: AsyncSession, bot: 'Bot') -> Dict[str, Any]:
        """
        Approve a specific free channel request and grant access to the user.

        Args:
            request_id: ID of the request to approve
            session: Database session
            bot: Bot instance for sending messages

        Returns:
            Dictionary with success status and message
        """
        try:
            # Get the specific request
            result = await session.execute(
                select(FreeChannelRequest).where(
                    FreeChannelRequest.id == request_id,
                    FreeChannelRequest.processed.is_(False)
                )
            )
            request = result.scalars().first()

            if not request:
                return {
                    "success": False,
                    "error": "Request not found or already processed"
                }

            # Get the bot configuration to get the free channel ID
            config = await ConfigService.get_bot_config(session)
            if not config.free_channel_id:
                return {
                    "success": False,
                    "error": "Free channel ID not configured"
                }

            # Grant access to the user by sending the channel invite link
            try:
                # Create an invite link for the free channel
                invite_link = await bot.create_chat_invite_link(
                    chat_id=config.free_channel_id,
                    member_limit=1,  # Single use invite
                    expire_date=datetime.now(timezone.utc) + timedelta(hours=24)  # Expire in 24 hours
                )

                # Send the invite to the user
                await bot.send_message(
                    chat_id=request.user_id,
                    text=(
                        "🎉 ¡Tu acceso ha sido aprobado!\n\n"
                        f"Únete al canal gratuito usando este enlace: {invite_link.invite_link}"
                    )
                )
            except Exception as e:
                # If sending invite fails, log the error and return failure
                # to avoid marking the request as approved incorrectly
                logging.exception(f"No se pudo enviar el enlace de invitación al usuario {request.user_id} para la solicitud {request.id}")
                return {
                    "success": False,
                    "error": f"No se pudo enviar el enlace de invitación: {str(e)}"
                }

            # Mark the request as processed and approved
            request.processed = True
            request.approved = True
            request.processed_date = datetime.now(timezone.utc)

            await session.commit()

            return {
                "success": True,
                "message": f"Request {request_id} approved successfully"
            }
        except SQLAlchemyError as e:
            await session.rollback()
            return {
                "success": False,
                "error": f"Database error: {str(e)}"
            }

    @staticmethod
    async def broadcast_post(target_channel_type: str, message_id: int, from_chat_id: int, use_reactions: bool, bot: 'Bot', session: AsyncSession) -> BroadcastResult:
        """
        Send a post to the target channel with optional reactions.

        Args:
            target_channel_type: 'vip' or 'free'
            message_id: ID of the message to be broadcasted
            from_chat_id: Chat ID where the original message is located
            use_reactions: Whether to add reaction buttons to the post
            bot: Bot instance for sending messages
            session: Database session

        Returns:
            Dictionary with success status and message
        """
        try:
            # Get the target channel ID from config
            config = await ConfigService.get_bot_config(session)

            if target_channel_type == 'vip':
                target_channel_id = config.vip_channel_id
            elif target_channel_type == 'free':
                target_channel_id = config.free_channel_id
            else:
                return {"success": False, "error": "Invalid channel type. Use 'vip' or 'free'."}

            if not target_channel_id:
                return {"success": False, "error": f"No {target_channel_type} channel ID configured."}

            # Prepare the reply markup based on use_reactions flag
            reply_markup = None
            if use_reactions:
                # Get the appropriate reaction list based on channel type using shared method
                reactions_list = await ConfigService.get_reactions_for_channel(session, target_channel_type)

                if reactions_list:
                    reply_markup = MenuFactory.create_reaction_keyboard(target_channel_type, reactions_list)

            # Copy the message to the target channel
            sent_message = await bot.copy_message(
                chat_id=target_channel_id,
                from_chat_id=from_chat_id,
                message_id=message_id,
                reply_markup=reply_markup
            )

            return {"success": True, "message_id": sent_message.message_id}
        except TelegramBadRequest as e:
            return {"success": False, "error": f"Telegram error: {str(e)}"}
        except Exception as e:
            logging.exception(f"Error broadcasting post to {target_channel_type} channel")
            return {"success": False, "error": f"Error inesperado al publicar: {str(e)}"}

    @staticmethod
    async def cleanup_old_requests(session: AsyncSession, days_old: int = 30) -> Dict[str, Any]:
        """
        Clean up old free channel requests that are older than specified days.

        Args:
            session: Database session
            days_old: Number of days to consider as "old" (default 30)

        Returns:
            Dictionary with success status and summary
        """
        try:
            # Calculate the date cutoff
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

            # Find old requests that haven't been processed
            result = await session.execute(
                select(FreeChannelRequest).where(
                    FreeChannelRequest.request_date < cutoff_date,
                    FreeChannelRequest.processed.is_(False)
                )
            )
            old_requests = result.scalars().all()

            count = len(old_requests)

            # Delete old requests
            for request in old_requests:
                await session.delete(request)

            await session.commit()

            return {
                "success": True,
                "message": f"Se limpiaron {count} solicitudes antiguas ({days_old}+ días)",
                "cleaned_count": count
            }
        except SQLAlchemyError as e:
            await session.rollback()
            return {
                "success": False,
                "error": f"Database error during cleanup: {str(e)}"
            }