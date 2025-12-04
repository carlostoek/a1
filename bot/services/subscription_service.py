"""
Service for managing VIP subscriptions and tokens.
"""
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from aiogram import Bot
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from aiogram.exceptions import TelegramBadRequest
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

    @staticmethod
    async def get_active_vip_subscription(user_id: int, session: AsyncSession):
        """
        Get a specific active VIP subscription for a user.

        Args:
            user_id: ID of the user to look up
            session: Database session

        Returns:
            UserSubscription object if found and active, None otherwise
        """
        try:
            result = await session.execute(
                select(UserSubscription).where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.role == "vip",
                    UserSubscription.status == "active",
                    UserSubscription.expiry_date > datetime.now(timezone.utc)
                )
            )
            return result.scalars().first()
        except SQLAlchemyError as e:
            raise SubscriptionError(f"Error retrieving VIP subscription: {str(e)}")

    @staticmethod
    async def get_active_vips_paginated(page: int, page_size: int, session: AsyncSession) -> tuple:
        """
        Get paginated list of active VIP subscribers.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            session: Database session

        Returns:
            Tuple of (list of UserSubscription objects, total count)
        """
        try:
            # Calculate offset
            offset = (page - 1) * page_size

            # Filter conditions shared between both queries
            filters = [
                UserSubscription.role == "vip",
                UserSubscription.status == "active",
                UserSubscription.expiry_date > datetime.now(timezone.utc)
            ]

            # Query 1: Get total count
            count_result = await session.execute(
                select(func.count(UserSubscription.id)).where(*filters)
            )
            total_count = count_result.scalar()

            # Query 2: Get paginated records
            query = select(UserSubscription).where(*filters).order_by(UserSubscription.expiry_date.asc()).offset(offset).limit(page_size)

            result = await session.execute(query)
            users = result.scalars().all()

            return users, total_count
        except SQLAlchemyError as e:
            raise SubscriptionError(f"Error retrieving paginated VIP subscribers: {str(e)}")

    @staticmethod
    async def revoke_vip_access(user_id: int, bot, session: AsyncSession) -> dict:
        """
        Revoke VIP access for a user by expelling them from the VIP channel and updating their status.

        Args:
            user_id: ID of user to revoke access
            bot: Bot instance to perform the expulsion
            session: Database session

        Returns:
            Dictionary with success status and message
        """
        try:
            # Get the bot configuration to get the VIP channel ID
            config = await ConfigService.get_bot_config(session)

            if not config.vip_channel_id:
                return {
                    "success": False,
                    "error": "VIP channel ID not configured"
                }

            # Find the user's active subscription
            result = await session.execute(
                select(UserSubscription).where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.role == "vip",
                    UserSubscription.status == "active",
                    UserSubscription.expiry_date > datetime.now(timezone.utc)
                )
            )
            subscription = result.scalars().first()

            if not subscription:
                return {
                    "success": False,
                    "error": "User does not have an active VIP subscription"
                }

            # Expel the user from the VIP channel
            try:
                await bot.ban_chat_member(chat_id=config.vip_channel_id, user_id=user_id)
                # Optionally unban immediately if we only want to kick (not permanently ban)
                # await bot.unban_chat_member(chat_id=config.vip_channel_id, user_id=user_id)
            except TelegramBadRequest as e:
                # If user is already banned or not in the channel, continue with DB update
                # This is acceptable since we're revoking their access anyway
                pass

            # Update the subscription status in the database
            subscription.status = "revoked"
            subscription.role = "free"

            await session.commit()

            return {
                "success": True,
                "message": f"VIP access revoked for user {user_id}"
            }
        except SQLAlchemyError as e:
            await session.rollback()
            return {
                "success": False,
                "error": f"Database error: {str(e)}"
            }
        except Exception as e:
            import logging
            logging.exception(f"Unexpected error revoking VIP access for user {user_id}")
            return {
                "success": False,
                "error": f"Error revoking VIP access: {str(e)}"
            }

    @staticmethod
    async def send_token_redemption_success(message: Message, tier: SubscriptionTier, session: AsyncSession) -> None:
        """
        Send a success message for token redemption with VIP channel invite link.

        Args:
            message: The message object from the user
            tier: The subscription tier that was redeemed
            session: Database session for getting bot config
        """

        bot_config = await ConfigService.get_bot_config(session)
        vip_channel_id = bot_config.vip_channel_id

        if not vip_channel_id:
            response_text = (
                f"✅ Token canjeado, pero el canal VIP no está configurado. "
                f"Contacta a un administrador."
            )
            await message.reply(response_text)
            return

        # Calculate expiry date to include in message
        duration_days = tier.duration_days
        expiry_date = datetime.now(timezone.utc) + timedelta(days=duration_days)

        # Create a chat invite link for the VIP channel
        try:
            invite_link = await message.bot.create_chat_invite_link(
                chat_id=vip_channel_id,
                member_limit=1,  # Single use invite
                expire_date=expiry_date  # Expire when subscription expires
            )

            response_text = (
                f"🎉 ¡Felicidades! Has canjeado un token para la tarifa **{tier.name}**.\n\n"
                f"Aquí tienes tu enlace de invitación único para el canal VIP. "
                f"Es válido solo para ti y expirará en {duration_days} días.\n\n"
                f"➡️ **[UNIRSE AL CANAL VIP]({invite_link.invite_link})**"
            )
            await message.reply(response_text, parse_mode="Markdown")
        except Exception as e:
            # If invite link creation fails, inform the user
            response_text = (
                f"✅ Token canjeado para la tarifa **{tier.name}** por {duration_days} días.\n"
                f"Sin embargo, hubo un error al generar el enlace de invitación. "
                f"Contacta a un administrador para acceso al canal VIP."
            )
            await message.reply(response_text)

    @staticmethod
    async def add_vip_days(user_id: int, days: int, session: AsyncSession) -> Dict[str, Any]:
        """
        Add VIP days to a user's subscription, handling different states appropriately.

        Args:
            user_id: ID of the user to add VIP days to
            days: Number of days to add
            session: Database session

        Returns:
            Dictionary with new expiry date and status information
        """
        try:
            # Get the current time
            now = datetime.now(timezone.utc)

            # Check for existing subscription
            result = await session.execute(
                select(UserSubscription).where(
                    UserSubscription.user_id == user_id
                )
            )
            existing_subscription = result.scalars().first()

            if existing_subscription:
                # Case A: User has existing subscription
                # Check if it's active and not expired
                is_active = (
                    existing_subscription.status == "active" and
                    existing_subscription.expiry_date > now
                )

                if is_active:
                    # Extend the current expiry date
                    extended_expiry = existing_subscription.expiry_date + timedelta(days=days)
                    existing_subscription.expiry_date = extended_expiry
                    existing_subscription.role = "vip"  # Ensure role is VIP
                else:
                    # Case B: User is expired or not active, start a new subscription
                    start_date = max(now, existing_subscription.expiry_date if existing_subscription.expiry_date else now)
                    new_expiry = start_date + timedelta(days=days)
                    existing_subscription.expiry_date = new_expiry
                    existing_subscription.status = "active"
                    existing_subscription.role = "vip"
            else:
                # Case C: User is new or has no record, create new subscription
                expiry_date = now + timedelta(days=days)
                new_subscription = UserSubscription(
                    user_id=user_id,
                    join_date=now,
                    expiry_date=expiry_date,
                    status="active",
                    role="vip"
                )
                session.add(new_subscription)

            await session.commit()

            # Return the new state information for notifications
            final_expiry = existing_subscription.expiry_date if existing_subscription else new_expiry
            return {
                "success": True,
                "new_expiry_date": final_expiry,
                "days_added": days,
                "status": "active",
                "role": "vip"
            }
        except SQLAlchemyError as e:
            await session.rollback()
            return {
                "success": False,
                "error": f"Database error: {str(e)}"
            }
        except Exception as e:
            await session.rollback()
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }