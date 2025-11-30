"""
User handlers for the Telegram Admin Bot.
Handles user interactions like token redemption and free channel access.
"""
import re
from aiogram import Router, F
from aiogram.types import Message
from datetime import datetime, timezone, timedelta
from aiogram.filters import Command
from bot.middlewares.db import DBSessionMiddleware
from bot.services.subscription_service import SubscriptionService
from bot.services.channel_service import ChannelManagementService
from bot.services.config_service import ConfigService

# Regular expression patterns compiled once at module level for efficiency
_UUID_PATTERN = re.compile(r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$')
_ALPHANUMERIC_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')


# Create router for user handlers
user_router = Router()
user_router.message.middleware(DBSessionMiddleware())


def looks_like_token(text: str) -> bool:
    """
    Check if the text looks like a token.
    A token typically has length > 5 and may match UUID format or similar.
    """
    # Check minimum length
    if len(text) < 6:
        return False

    # Check if it contains alphanumeric characters and hyphens (like UUID)
    if _UUID_PATTERN.match(text):
        return True

    # Check if it looks like an alphanumeric token (at least 6 characters)
    if _ALPHANUMERIC_PATTERN.match(text) and len(text) >= 6:
        return True

    return False




@user_router.message(~F.text.startswith('/'))  # Only process non-command messages
async def process_user_message(message: Message, session):
    """
    Process user messages - could be tokens or requests for free access.
    Trigger: Any text message that is not a command.
    """
    if not message.text:
        return  # Ignore if there's no text

    text = message.text.strip()

    # Check if the message looks like a token
    if looks_like_token(text):
        # Attempt to redeem the token
        result = await SubscriptionService.redeem_token(session, message.from_user.id, text)

        if result["success"]:
            # Success: token was redeemed
            tier = result["tier"]
            duration_days = tier.duration_days
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
        else:
            # Error: token was invalid
            error = result["error"]
            response_text = f"❌ Token inválido o expirado. Motivo: {error}"
            await message.reply(response_text)
    else:
        # Text doesn't look like a token, treat as a request for free channel access
        # This handles users who arrive and interact with the bot for the first time
        result = await ChannelManagementService.request_free_access(session, message.from_user.id)

        if result["status"] == "already_requested":
            wait_minutes = result["wait_minutes"]
            remaining_minutes = result["remaining_minutes"]
            response_text = (
                f"⏳ Ya tienes una solicitud pendiente.\n"
                f"Tiempo restante: {max(0, remaining_minutes)} minutos de {wait_minutes} minutos de espera."
            )
            await message.reply(response_text)
        elif result["status"] == "queued":
            wait_minutes = result["wait_minutes"]
            response_text = (
                f"⏳ Tu tiempo de espera es {wait_minutes} minutos.\n"
                f"El bot te enviará el enlace automáticamente cuando pase el tiempo. ¡No bloquees al bot!"
            )
            await message.reply(response_text)