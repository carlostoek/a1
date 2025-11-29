"""
User handlers for the Telegram Admin Bot.
Handles user interactions like token redemption.
"""
import re
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from bot.middlewares.db import DBSessionMiddleware
from bot.services.subscription_service import SubscriptionService


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
    uuid_pattern = re.compile(r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$')
    if uuid_pattern.match(text):
        return True
    
    # Check if it looks like an alphanumeric token (at least 6 characters)
    alphanumeric_pattern = re.compile(r'^[a-zA-Z0-9_-]+$')
    if alphanumeric_pattern.match(text) and len(text) >= 6:
        return True
    
    return False


@user_router.message(~F.text.startswith('/'))  # Only process non-command messages
async def process_token_message(message: Message, session):
    """
    Process messages that might contain tokens.
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
            duration = result["duration"]
            expiry = result["expiry"].strftime('%Y-%m-%d %H:%M:%S UTC')
            response_text = f"✅ Token canjeado. Tienes acceso por {duration} horas. Fecha de expiración: {expiry}"
            await message.reply(response_text)
        else:
            # Error: token was invalid
            error = result["error"]
            response_text = f"❌ Token inválido o expirado. Motivo: {error}"
            await message.reply(response_text)
    else:
        # Text doesn't look like a token, ignore or provide help message
        # For now, we'll ignore non-token-like messages so they don't interfere with admin functions
        pass