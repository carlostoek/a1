"""
Service for managing VIP subscriptions and tokens.
"""
import uuid
from typing import Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from bot.database.models import (
    InvitationToken,
    VIPSubscriber,
    BotConfig
)
from bot.services.exceptions import (
    TokenInvalidError,
    TokenNotFoundError,
    SubscriptionError
)


class SubscriptionService:
    """
    Service for managing VIP subscriptions and invitation tokens.
    """
    
    @staticmethod
    async def generate_vip_token(
        session: AsyncSession, 
        admin_id: int, 
        duration_hours: int
    ) -> InvitationToken:
        """
        Generate a new VIP invitation token.
        """
        try:
            # Generate a unique token string
            token_str = str(uuid.uuid4())
            
            # Create the invitation token
            token = InvitationToken(
                token=token_str,
                generated_by=admin_id,
                duration_hours=duration_hours
            )
            
            session.add(token)
            await session.commit()
            await session.refresh(token)
            
            return token
        except Exception as e:
            await session.rollback()
            raise SubscriptionError(f"Error generating VIP token: {str(e)}")
    
    @staticmethod
    async def validate_token(session: AsyncSession, token_str: str) -> Optional[InvitationToken]:
        """
        Validate a token and return the token object if it's valid and unused.
        """
        try:
            # Query for the token
            result = await session.execute(
                select(InvitationToken).where(
                    InvitationToken.token == token_str,
                    InvitationToken.used == False  # noqa: E712
                )
            )
            token = result.scalars().first()
            
            return token
        except Exception as e:
            raise TokenInvalidError(f"Error validating token: {str(e)}")
    
    @staticmethod
    async def register_subscription(
        session: AsyncSession, 
        user_id: int, 
        token_id: int, 
        duration_hours: int
    ) -> VIPSubscriber:
        """
        Register a new VIP subscription using a valid token.
        Marks the token as used and creates a subscription record.
        """
        try:
            # Get the token
            result = await session.execute(
                select(InvitationToken).where(
                    InvitationToken.id == token_id,
                    InvitationToken.used == False  # noqa: E712
                )
            )
            token = result.scalars().first()
            
            if not token:
                raise TokenNotFoundError(f"Token with ID {token_id} not found or already used")
            
            # Calculate expiry date from current time + duration
            expiry_date = datetime.now(timezone.utc) + timedelta(hours=duration_hours)

            # Create the VIP subscriber record
            subscriber = VIPSubscriber(
                user_id=user_id,
                join_date=datetime.now(timezone.utc),
                expiry_date=expiry_date,
                status="active",
                token_id=token.id
            )
            
            # Mark the token as used
            token.used = True
            token.used_by = user_id
            token.used_at = datetime.now(timezone.utc)
            
            # Add the subscriber to the session
            session.add(subscriber)
            session.add(token)
            
            await session.commit()
            await session.refresh(subscriber)
            
            return subscriber
        except IntegrityError:
            await session.rollback()
            raise SubscriptionError("Failed to register subscription due to database integrity error")
        except Exception as e:
            await session.rollback()
            raise SubscriptionError(f"Error registering subscription: {str(e)}")
    
    @staticmethod
    async def check_subscription_status(session: AsyncSession, user_id: int) -> bool:
        """
        Check if a user has an active subscription.
        """
        try:
            # Get the current time for comparison
            current_time = datetime.now(timezone.utc)

            # Query for active subscription that hasn't expired
            result = await session.execute(
                select(VIPSubscriber).where(
                    VIPSubscriber.user_id == user_id,
                    VIPSubscriber.status == "active",
                    VIPSubscriber.expiry_date > current_time
                )
            )
            subscriber = result.scalars().first()

            return subscriber is not None
        except Exception as e:
            raise SubscriptionError(f"Error checking subscription status: {str(e)}")