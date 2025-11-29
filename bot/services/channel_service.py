"""
Service for managing channel requests and statistics.
"""
from typing import List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from bot.database.models import FreeChannelRequest, VIPSubscriber
from bot.services.exceptions import ServiceError


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
                    select(func.count(VIPSubscriber.id)).where(
                        VIPSubscriber.status == "active",
                        VIPSubscriber.expiry_date > datetime.now(timezone.utc)
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