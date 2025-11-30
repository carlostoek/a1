"""
Service for managing VIP subscriptions and tokens.
"""
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from bot.database.models import (
    InvitationToken,
    UserSubscription,
    SubscriptionTier
)
from bot.services.config_service import ConfigService
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
        tier_id: int,
        bot: Bot
    ) -> str:
        """
        Generate a new VIP invitation token link.
        """
        try:
            # Check if the tier exists
            tier = await ConfigService.get_tier_by_id(session, tier_id)
            if not tier:
                raise SubscriptionError(f"Subscription tier with ID {tier_id} not found.")

            # Generate a unique token string
            token_str = str(uuid.uuid4())

            # Create the invitation token
            token = InvitationToken(
                token=token_str,
                generated_by=admin_id,
                tier_id=tier_id
            )

            session.add(token)
            await session.commit()

            # Get bot username to create the link
            bot_user = await bot.me()
            bot_username = bot_user.username
            
            return f"https://t.me/{bot_username}?start={token_str}"
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
        token_id: int
    ) -> UserSubscription:
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

            # Get tier to determine duration
            tier = await ConfigService.get_tier_by_id(session, token.tier_id)
            if not tier:
                raise SubscriptionError(f"Associated subscription tier not found for token {token_id}")

            # Calculate expiry date from current time + duration
            now = datetime.now(timezone.utc)
            expiry_date = now + timedelta(days=tier.duration_days)

            # Create the VIP subscriber record
            subscriber = UserSubscription(
                user_id=user_id,
                join_date=now,
                expiry_date=expiry_date,
                status="active",
                role="vip",
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
                select(UserSubscription).where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.status == "active",
                    UserSubscription.expiry_date > current_time
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
        """
        try:
            # Search for the token in the database
            token = await SubscriptionService.validate_token(session, token_str)

            if not token:
                return {"success": False, "error": "Token no válido o ya ha sido usado"}

            # Get the tier details for duration
            tier = await ConfigService.get_tier_by_id(session, token.tier_id)
            if not tier:
                return {"success": False, "error": "La tarifa de suscripción asociada a este token ya no existe."}

            duration_days = tier.duration_days

            # Mark token as used
            token.used = True
            token.used_by = user_id
            token.used_at = datetime.now(timezone.utc)

            # Check for existing subscription to extend it
            result = await session.execute(select(UserSubscription).where(UserSubscription.user_id == user_id))
            subscriber = result.scalars().first()
            
            now = datetime.now(timezone.utc)

            if subscriber:
                # If subscription is expired, start new one from now. Otherwise, extend.
                # Ensure subscriber.expiry_date is timezone-aware for comparison
                existing_expiry = subscriber.expiry_date
                if existing_expiry and existing_expiry.tzinfo is None:
                    # Make it timezone-aware assuming it's in UTC
                    existing_expiry = existing_expiry.replace(tzinfo=timezone.utc)

                start_date = max(now, existing_expiry or now)
                subscriber.expiry_date = start_date + timedelta(days=duration_days)
                subscriber.status = "active"
                subscriber.role = "vip"
                subscriber.token_id = token.id
            else:
                # Create a new subscription
                subscriber = UserSubscription(
                    user_id=user_id,
                    join_date=now,
                    expiry_date=now + timedelta(days=duration_days),
                    status="active",
                    role="vip",
                    token_id=token.id,
                )
                session.add(subscriber)
            
            await session.commit()

            return {
                "success": True,
                "tier": tier
            }
        except (TokenInvalidError, SubscriptionError) as e:
            await session.rollback()
            raise SubscriptionError(f"Error redeeming token: {e}")
        except SQLAlchemyError as e:
            await session.rollback()
            raise SubscriptionError(f"Database error during token redemption: {e}")