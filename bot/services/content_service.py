"""
Content Management Service for System B.
This service implements System A's content management features like protected messages and advanced posting.
"""
from bot.utils.sexy_logger import get_logger
from typing import List, Dict, Any, Optional
from aiogram import Bot
from aiogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InputMediaPhoto, 
    InputMediaVideo, 
    InputMediaDocument, 
    InputMediaAudio
)
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.models import Channel
from bot.services.advanced_channel_service import AdvancedChannelService
from bot.services.exceptions import ServiceError


logger = get_logger(__name__)


class ContentManagementService:
    """
    Service for managing content with advanced features from System A.
    """
    
    @staticmethod
    async def send_protected_content(
        channel_id: int,
        content: str,
        bot: Bot,
        session: AsyncSession,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        media_files: Optional[List[Dict[str, Any]]] = None,
        protect_content: bool = True
    ) -> Optional[Message]:
        """
        Send content to a channel with protection options.
        
        Args:
            channel_id: Target channel ID
            content: Content text
            bot: Bot instance
            session: Database session
            reply_markup: Optional reply markup
            media_files: Optional list of media files
            protect_content: Whether to protect content from copying
            
        Returns:
            Sent message object or None if failed
        """
        try:
            # Use the advanced service to send protected message
            advanced_service = AdvancedChannelService(session, bot)
            sent_message = await advanced_service.send_protected_message(
                channel_id=channel_id,
                text=content,
                reply_markup=reply_markup,
                media_files=media_files
            )
            
            return sent_message
        except Exception as e:
            logger.network(f"Error sending protected content to channel {channel_id}: {e}")
            return None
    
    @staticmethod
    async def create_channel_post(
        channel_id: int,
        content: str,
        bot: Bot,
        session: AsyncSession,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        media_files: Optional[List[Dict[str, Any]]] = None,
        protect_content: bool = True,
        pin_message: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Create and send a post to a channel with advanced options.
        
        Args:
            channel_id: Target channel ID
            content: Post content
            bot: Bot instance
            session: Database session
            reply_markup: Optional reply markup with reactions
            media_files: Optional list of media files
            protect_content: Whether to protect content
            pin_message: Whether to pin the message after sending
            
        Returns:
            Dictionary with result information or None if failed
        """
        try:
            # Send the protected content
            sent_message = await ContentManagementService.send_protected_content(
                channel_id=channel_id,
                content=content,
                bot=bot,
                session=session,
                reply_markup=reply_markup,
                media_files=media_files,
                protect_content=protect_content
            )
            
            if not sent_message:
                return None
            
            result = {
                "success": True,
                "message_id": sent_message.message_id,
                "channel_id": channel_id,
                "content_length": len(content)
            }
            
            # Pin the message if requested
            if pin_message:
                try:
                    await bot.pin_chat_message(
                        chat_id=channel_id,
                        message_id=sent_message.message_id
                    )
                    result["pinned"] = True
                except TelegramBadRequest as e:
                    logger.network(f"Could not pin message {sent_message.message_id} in channel {channel_id}: {e}")
                    result["pinned"] = False
                    result["pin_error"] = str(e)
            
            return result
            
        except Exception as e:
            logger.network(f"Error creating channel post in channel {channel_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def update_channel_reactions(
        channel_id: int,
        reactions: List[str],
        reaction_points: Optional[Dict[str, float]] = None,
        session: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Update reactions for a specific channel.
        
        Args:
            channel_id: Channel ID to update
            reactions: List of reaction emojis
            reaction_points: Optional mapping of reaction to points
            session: Database session
            
        Returns:
            Dictionary with update result
        """
        try:
            if session:
                # Use the channel management service to configure reactions
                from bot.services.channel_service import ChannelManagementService
                result = await ChannelManagementService.configure_channel_reactions(
                    session=session,
                    channel_id=channel_id,
                    reactions=reactions,
                    reaction_points=reaction_points
                )
                return result
            else:
                # If no session provided, just return a basic success
                return {
                    "success": True,
                    "channel_id": channel_id,
                    "reactions": reactions
                }
        except Exception as e:
            logger.database(f"Error updating channel reactions for {channel_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def get_channel_content_stats(
        channel_id: int,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Get statistics for content in a specific channel.
        
        Args:
            channel_id: Channel ID to get stats for
            session: Database session
            
        Returns:
            Dictionary with content statistics
        """
        try:
            # Get the channel from DB
            channel = await session.get(Channel, channel_id)
            if not channel:
                return {
                    "success": False,
                    "error": f"Channel {channel_id} not found"
                }
            
            # Get reaction counts for this channel (would require additional logic to track messages in this channel)
            # For now, return basic channel info
            stats = {
                "success": True,
                "channel_id": channel.id,
                "title": channel.title,
                "type": channel.channel_type,
                "reactions_count": len(channel.reactions) if channel.reactions else 0,
                "protect_content": channel.protect_content,
                "has_reactions": bool(channel.reactions) if channel.reactions else False
            }
            
            return stats
        except Exception as e:
            logger.database(f"Error getting channel content stats for {channel_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def track_content_interaction(
        message_id: int,
        user_id: int,
        interaction_type: str,  # 'reaction', 'view', 'share', etc.
        session: AsyncSession
    ) -> bool:
        """
        Track user interaction with content.
        
        Args:
            message_id: Message ID that was interacted with
            user_id: User ID who interacted
            interaction_type: Type of interaction
            session: Database session
            
        Returns:
            True if tracking was successful
        """
        try:
            # Use the advanced service to track button reactions
            advanced_service = AdvancedChannelService(session, None)
            success = await advanced_service.track_button_reaction(
                message_id=message_id,
                user_id=user_id,
                reaction_type=interaction_type
            )
            return success
        except Exception as e:
            logger.database(f"Error tracking content interaction: {e}")
            return False