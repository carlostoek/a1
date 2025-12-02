"""
Service for retrieving and aggregating statistics for the Telegram Admin Bot.
"""
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from bot.database.models import UserSubscription, InvitationToken, FreeChannelRequest
from bot.services.config_service import ConfigService


class StatsService:
    """
    Service class for retrieving and aggregating various statistics for the bot.
    """

    @staticmethod
    async def get_general_stats(session: AsyncSession) -> Dict[str, Any]:
        """
        Get general statistics for the bot.

        Args:
            session: Database session for queries

        Returns:
            Dictionary containing general stats
        """
        try:
            # Count total distinct users registered in UserSubscription
            total_users_result = await session.execute(
                select(func.count(func.distinct(UserSubscription.user_id)))
            )
            total_users = total_users_result.scalar() or 0

            # Count total active VIP subscribers
            active_vip_result = await session.execute(
                select(func.count(UserSubscription.id)).where(
                    UserSubscription.role == "vip",
                    UserSubscription.status == "active"
                )
            )
            active_vip = active_vip_result.scalar() or 0

            # Count total expired or revoked VIP subscribers
            expired_revoked_vip_result = await session.execute(
                select(func.count(UserSubscription.id)).where(
                    UserSubscription.role == "vip",
                    UserSubscription.status.in_(["expired", "revoked"])
                )
            )
            expired_revoked_vip = expired_revoked_vip_result.scalar() or 0

            # Count total invitation tokens generated
            total_tokens_result = await session.execute(
                select(func.count(InvitationToken.id))
            )
            total_tokens_generated = total_tokens_result.scalar() or 0

            # Placeholder for revenue: total_revenue = 0.00
            total_revenue = 0.00

            # Construct and return the stats dictionary
            return {
                "total_users": total_users,
                "active_vip": active_vip,
                "expired_revoked_vip": expired_revoked_vip,
                "tokens_generated": total_tokens_generated,
                "total_revenue": total_revenue
            }
        except Exception as e:
            raise Exception(f"Error retrieving general stats: {str(e)}")

    @staticmethod
    async def get_vip_stats(session: AsyncSession) -> Dict[str, Any]:
        """
        Get VIP subscription statistics.

        Args:
            session: Database session for queries

        Returns:
            Dictionary containing VIP stats
        """
        try:
            # Count VIPs active per SubscriptionTier
            from bot.services.config_service import ConfigService
            tiers = await ConfigService.get_all_tiers(session)

            # Initialize dictionary with tier IDs and zero counts
            tier_counts = {}
            for tier in tiers:
                if tier.is_active:  # Only count active tiers
                    tier_count_result = await session.execute(
                        select(func.count(UserSubscription.id)).where(
                            UserSubscription.role == "vip",
                            UserSubscription.status == "active",
                            UserSubscription.token_id == tier.id  # This might need adjustment depending on the data model
                        )
                    )
                    tier_counts[tier.id] = tier_count_result.scalar() or 0

            # Actually, let's count using the token relationship to get tier-based stats
            # Get all active subscriptions and group by token_id which corresponds to tier_id
            active_subscriptions_result = await session.execute(
                select(UserSubscription.token_id, func.count(UserSubscription.id)).where(
                    UserSubscription.role == "vip",
                    UserSubscription.status == "active",
                    UserSubscription.token_id.isnot(None)
                ).group_by(UserSubscription.token_id)
            )
            tier_counts = dict(active_subscriptions_result.all())

            # Count total invitation tokens redeemed
            redeemed_tokens_result = await session.execute(
                select(func.count(InvitationToken.id)).where(
                    InvitationToken.used.is_(True)
                )
            )
            total_tokens_redeemed = redeemed_tokens_result.scalar() or 0

            # Count total invitation tokens expired or inactive
            from datetime import datetime, timezone
            expired_tokens_result = await session.execute(
                select(func.count(InvitationToken.id)).where(
                    InvitationToken.expiry_date < datetime.now(timezone.utc),
                    InvitationToken.used.is_(False)
                )
            )
            total_expired_tokens = expired_tokens_result.scalar() or 0

            # Construct and return the stats dictionary
            return {
                "tier_counts": tier_counts,
                "tokens_redeemed": total_tokens_redeemed,
                "tokens_expired_unused": total_expired_tokens
            }
        except Exception as e:
            raise Exception(f"Error retrieving VIP stats: {str(e)}")

    @staticmethod
    async def get_free_channel_stats(session: AsyncSession) -> Dict[str, Any]:
        """
        Get free channel request statistics.

        Args:
            session: Database session for queries

        Returns:
            Dictionary containing free channel stats
        """
        try:
            # Count pending requests
            pending_result = await session.execute(
                select(func.count(FreeChannelRequest.id)).where(
                    FreeChannelRequest.processed.is_(False)
                )
            )
            pending_count = pending_result.scalar() or 0

            # Count processed requests (historical)
            processed_result = await session.execute(
                select(func.count(FreeChannelRequest.id)).where(
                    FreeChannelRequest.processed.is_(True),
                    FreeChannelRequest.approved.is_(True)
                )
            )
            processed_count = processed_result.scalar() or 0

            # Count rejected/cleaned requests (historical)
            rejected_result = await session.execute(
                select(func.count(FreeChannelRequest.id)).where(
                    FreeChannelRequest.processed.is_(True),
                    FreeChannelRequest.approved.is_(False)
                )
            )
            rejected_count = rejected_result.scalar() or 0

            # Construct and return the stats dictionary
            return {
                "pending_count": pending_count,
                "processed_count": processed_count,
                "rejected_count": rejected_count
            }
        except Exception as e:
            raise Exception(f"Error retrieving free channel stats: {str(e)}")