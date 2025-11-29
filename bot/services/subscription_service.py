"""
Service for managing VIP subscriptions and tokens.
"""
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from bot.database.models import (
    InvitationToken,
    VIPSubscriber
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
        except SQLAlchemyError as e:
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
                    InvitationToken.used.is_(False)
                )
            )
            token = result.scalars().first()

            return token
        except SQLAlchemyError as e:
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
                    InvitationToken.used.is_(False)
                )
            )
            token = result.scalars().first()

            if not token:
                raise TokenNotFoundError(f"Token with ID {token_id} not found or already used")

            # Calculate expiry date from current time + duration
            now = datetime.now(timezone.utc)
            expiry_date = now + timedelta(hours=duration_hours)

            # Create the VIP subscriber record
            subscriber = VIPSubscriber(
                user_id=user_id,
                join_date=now,
                expiry_date=expiry_date,
                status="active",
                token_id=token.id
            )

            # Mark the token as used
            token.used = True
            token.used_by = user_id
            token.used_at = now

            # Add the subscriber to the session
            session.add(subscriber)
            session.add(token)

            await session.commit()
            await session.refresh(subscriber)

            return subscriber
        except IntegrityError:
            await session.rollback()
            raise SubscriptionError("Failed to register subscription due to database integrity error")
        except SQLAlchemyError as e:
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
        except SQLAlchemyError as e:
            raise SubscriptionError(f"Error checking subscription status: {str(e)}")

    @staticmethod
    async def redeem_token(session: AsyncSession, user_id: int, token_str: str) -> Dict[str, Any]:
        """
        Redeem a VIP token.

        Args:
            session: Database session
            user_id: ID of the user redeeming the token
            token_str: The token string to redeem

        Returns:
            Dictionary with success status and token details or error message
        """
        try:
            # Search for the token in the database
            result = await session.execute(
                select(InvitationToken).where(
                    InvitationToken.token == token_str
                )
            )
            token = result.scalars().first()

            if not token:
                return {
                    "success": False,
                    "error": "Token no encontrado"
                }

            # Check if token is already used
            if token.used:
                return {
                    "success": False,
                    "error": "Token ya ha sido usado"
                }

            # Check if token has expired (compare creation time + duration vs current time)
            token_expiration_time = token.created_at + timedelta(hours=token.duration_hours)
            current_time = datetime.now(timezone.utc)

            if current_time > token_expiration_time:
                return {
                    "success": False,
                    "error": "Token ha expirado"
                }

            # Token is valid, mark it as used
            token.used = True
            token.used_by = user_id
            token.used_at = datetime.now(timezone.utc)

            # Create/update VIP subscription for the user
            expiry_date = datetime.now(timezone.utc) + timedelta(hours=token.duration_hours)

            # Check if user already has a subscription
            existing_subscriber_result = await session.execute(
                select(VIPSubscriber).where(
                    VIPSubscriber.user_id == user_id
                )
            )
            existing_subscriber = existing_subscriber_result.scalars().first()

            if existing_subscriber:
                # Update existing subscription (extend the expiry date)
                if existing_subscriber.expiry_date > datetime.now(timezone.utc):
                    # If current subscription is still valid, extend from its expiry date
                    existing_subscriber.expiry_date = expiry_date
                else:
                    # If current subscription has expired, set to new expiry date
                    existing_subscriber.expiry_date = expiry_date
                existing_subscriber.status = "active"
                existing_subscriber.token_id = token.id
            else:
                # Create new subscription
                subscriber = VIPSubscriber(
                    user_id=user_id,
                    join_date=datetime.now(timezone.utc),
                    expiry_date=expiry_date,
                    status="active",
                    token_id=token.id
                )
                session.add(subscriber)

            # Commit changes to the database
            await session.commit()

            return {
                "success": True,
                "duration": token.duration_hours,
                "expiry": expiry_date
            }
        except SQLAlchemyError as e:
            await session.rollback()
            raise SubscriptionError(f"Error validating token: {str(e)}")