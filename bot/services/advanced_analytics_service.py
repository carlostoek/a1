"""
Advanced Channel Management Service for System B.
This service provides advanced features from System A like detailed statistics, 
user onboarding, and advanced moderation tools.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from aiogram import Bot
from bot.database.models import (
    Channel, 
    UserSubscription, 
    FreeChannelRequest, 
    PendingChannelRequest, 
    ButtonReaction,
    BotConfig
)
from bot.services.config_service import ConfigService
from bot.services.advanced_channel_service import AdvancedChannelService
from bot.services.exceptions import ServiceError


logger = logging.getLogger(__name__)


class AdvancedAnalyticsService:
    """
    Service for advanced analytics and statistics for channels.
    """
    
    @staticmethod
    async def get_detailed_channel_statistics(session: AsyncSession, bot: Bot) -> Dict[str, Any]:
        """
        Get comprehensive statistics for all channels.
        
        Args:
            session: Database session
            bot: Bot instance for additional Telegram API calls
            
        Returns:
            Dictionary with detailed channel statistics
        """
        try:
            # Get basic channel stats using the advanced service
            advanced_service = AdvancedChannelService(session, bot)
            basic_stats = await advanced_service.get_channel_statistics()
            
            # Get additional metrics
            # 1. User engagement metrics
            recent_engagement_result = await session.execute(
                select(func.count(ButtonReaction.id)).where(
                    ButtonReaction.created_at > datetime.now() - timedelta(days=7)
                )
            )
            recent_engagement = recent_engagement_result.scalar() or 0
            
            # 2. Request processing metrics
            recent_requests_result = await session.execute(
                select(func.count(FreeChannelRequest.id)).where(
                    FreeChannelRequest.request_date > datetime.now() - timedelta(days=7)
                )
            )
            recent_requests = recent_requests_result.scalar() or 0
            
            # 3. VIP conversion metrics
            vip_conversion_result = await session.execute(
                select(func.count(UserSubscription.id)).where(
                    and_(
                        UserSubscription.role == "vip",
                        UserSubscription.join_date > datetime.now() - timedelta(days=7)
                    )
                )
            )
            new_vip_users = vip_conversion_result.scalar() or 0
            
            # 4. Channel-specific metrics
            all_channels = await advanced_service.list_channels()
            channel_details = []
            
            for channel in all_channels:
                # Get member count from Telegram API if possible
                member_count = 0
                try:
                    member_count = await bot.get_chat_member_count(channel.id)
                except Exception:
                    # If we can't get member count, skip or use 0
                    pass
                
                channel_details.append({
                    "id": channel.id,
                    "title": channel.title,
                    "type": channel.channel_type,
                    "member_count": member_count,
                    "reactions_count": len(channel.reactions) if channel.reactions else 0,
                    "protect_content": channel.protect_content
                })
            
            # 5. Pending request metrics
            pending_requests_result = await session.execute(
                select(func.count(PendingChannelRequest.id)).where(
                    PendingChannelRequest.approved == False
                )
            )
            pending_requests_count = pending_requests_result.scalar() or 0
            
            # 6. Processed requests in last 24 hours
            processed_recent_result = await session.execute(
                select(func.count(PendingChannelRequest.id)).where(
                    and_(
                        PendingChannelRequest.approved == True,
                        PendingChannelRequest.processed_at > datetime.now() - timedelta(hours=24)
                    )
                )
            )
            processed_recent = processed_recent_result.scalar() or 0
            
            detailed_stats = {
                "basic": basic_stats,
                "engagement": {
                    "recent_interactions": recent_engagement,
                    "recent_requests": recent_requests,
                    "new_vip_conversions": new_vip_users
                },
                "channels": channel_details,
                "requests": {
                    "pending_count": pending_requests_count,
                    "processed_last_24h": processed_recent
                },
                "timestamp": datetime.now().isoformat()
            }
            
            return detailed_stats
            
        except Exception as e:
            logger.error(f"Error getting detailed channel statistics: {e}")
            raise ServiceError(f"Error getting detailed statistics: {str(e)}")
    
    @staticmethod
    async def get_user_onboarding_statistics(session: AsyncSession) -> Dict[str, Any]:
        """
        Get statistics related to user onboarding and retention.
        
        Args:
            session: Database session
            
        Returns:
            Dictionary with user onboarding statistics
        """
        try:
            # Calculate various onboarding metrics
            total_users_result = await session.execute(
                select(func.count(UserSubscription.user_id).distinct())
            )
            total_users = total_users_result.scalar() or 0
            
            active_users_result = await session.execute(
                select(func.count(UserSubscription.id)).where(
                    UserSubscription.status == "active"
                )
            )
            active_users = active_users_result.scalar() or 0
            
            # Users who went from free to VIP
            free_to_vip_result = await session.execute(
                select(func.count(UserSubscription.id)).where(
                    and_(
                        UserSubscription.role == "vip",
                        UserSubscription.join_date > datetime.now() - timedelta(days=30)
                    )
                )
            )
            free_to_vip_count = free_to_vip_result.scalar() or 0
            
            # Average time from free to VIP conversion
            # This requires more complex query to track user journey
            avg_conversion_time = 0  # Placeholder - would need more complex logic
            
            # Request completion rate
            total_requests_result = await session.execute(
                select(func.count(FreeChannelRequest.id))
            )
            total_requests = total_requests_result.scalar() or 0
            
            completed_requests_result = await session.execute(
                select(func.count(FreeChannelRequest.id)).where(
                    FreeChannelRequest.processed == True
                )
            )
            completed_requests = completed_requests_result.scalar() or 0
            
            completion_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
            
            onboarding_stats = {
                "total_users": total_users,
                "active_users": active_users,
                "free_to_vip_conversions": free_to_vip_count,
                "avg_conversion_time_days": avg_conversion_time,
                "request_completion_rate": completion_rate,
                "completed_requests": completed_requests,
                "total_requests": total_requests
            }
            
            return onboarding_stats
            
        except Exception as e:
            logger.error(f"Error getting user onboarding statistics: {e}")
            raise ServiceError(f"Error getting onboarding statistics: {str(e)}")
    
    @staticmethod
    async def get_reaction_analytics(session: AsyncSession, channel_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get analytics for reactions on channel posts.
        
        Args:
            session: Database session
            channel_id: Optional channel ID to filter analytics
            
        Returns:
            Dictionary with reaction analytics
        """
        try:
            query = select(ButtonReaction)
            
            if channel_id:
                # If channel_id is provided, we'd need to associate message IDs with channels
                # This requires additional logic to track which messages belong to which channels
                # For now, we'll return general reaction analytics
                pass
            
            result = await session.execute(query)
            reactions = result.scalars().all()
            
            # Count reactions by type
            reaction_counts = {}
            user_reaction_counts = {}
            
            for reaction in reactions:
                # Count by reaction type
                reaction_type = reaction.reaction_type
                reaction_counts[reaction_type] = reaction_counts.get(reaction_type, 0) + 1
                
                # Count reactions per user
                user_id = reaction.user_id
                user_reaction_counts[user_id] = user_reaction_counts.get(user_id, 0) + 1
            
            # Calculate top reactions
            top_reactions = sorted(reaction_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Calculate top reactors
            top_reactors = sorted(user_reaction_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            analytics = {
                "total_reactions": len(reactions),
                "reaction_types": reaction_counts,
                "top_reactions": top_reactions,
                "top_reactors": top_reactors,
                "unique_users": len(user_reaction_counts)
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting reaction analytics: {e}")
            raise ServiceError(f"Error getting reaction analytics: {str(e)}")
    
    @staticmethod
    async def get_channel_performance_report(session: AsyncSession, bot: Bot, days: int = 30) -> Dict[str, Any]:
        """
        Get a comprehensive performance report for channels.
        
        Args:
            session: Database session
            bot: Bot instance for additional metrics
            days: Number of days to include in the report
            
        Returns:
            Dictionary with channel performance report
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # Get metrics for the specified period
            # 1. New user requests
            new_requests_result = await session.execute(
                select(func.count(FreeChannelRequest.id)).where(
                    FreeChannelRequest.request_date > start_date
                )
            )
            new_requests = new_requests_result.scalar() or 0
            
            # 2. Processed requests
            processed_requests_result = await session.execute(
                select(func.count(PendingChannelRequest.id)).where(
                    and_(
                        PendingChannelRequest.approved == True,
                        PendingChannelRequest.processed_at > start_date
                    )
                )
            )
            processed_requests = processed_requests_result.scalar() or 0
            
            # 3. New VIP subscriptions
            new_vip_result = await session.execute(
                select(func.count(UserSubscription.id)).where(
                    and_(
                        UserSubscription.role == "vip",
                        UserSubscription.join_date > start_date
                    )
                )
            )
            new_vip = new_vip_result.scalar() or 0
            
            # 4. Active users
            active_users_result = await session.execute(
                select(func.count(UserSubscription.id)).where(
                    and_(
                        UserSubscription.status == "active",
                        or_(
                            UserSubscription.expiry_date.is_(None),
                            UserSubscription.expiry_date > datetime.now()
                        )
                    )
                )
            )
            active_users = active_users_result.scalar() or 0
            
            # 5. Reaction engagement
            reaction_engagement_result = await session.execute(
                select(func.count(ButtonReaction.id)).where(
                    ButtonReaction.created_at > start_date
                )
            )
            reaction_engagement = reaction_engagement_result.scalar() or 0
            
            # Calculate rates
            processing_rate = (processed_requests / new_requests * 100) if new_requests > 0 else 0
            conversion_rate = (new_vip / new_requests * 100) if new_requests > 0 else 0
            
            report = {
                "period_days": days,
                "start_date": start_date.isoformat(),
                "end_date": datetime.now().isoformat(),
                "metrics": {
                    "new_requests": new_requests,
                    "processed_requests": processed_requests,
                    "new_vip_subscriptions": new_vip,
                    "active_users": active_users,
                    "reaction_engagements": reaction_engagement
                },
                "rates": {
                    "processing_rate": round(processing_rate, 2),
                    "conversion_rate": round(conversion_rate, 2)
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error getting channel performance report: {e}")
            raise ServiceError(f"Error getting performance report: {str(e)}")