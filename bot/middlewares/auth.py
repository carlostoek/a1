"""
Admin authentication middleware to check if user is authorized.
"""
from typing import Callable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, CallbackQuery
from bot.config import Settings


ACCESS_DENIED_MESSAGE = "Acceso denegado"


class AdminAuthMiddleware(BaseMiddleware):
    """
    Middleware that checks if the user is in the admin list.
    If not an admin, sends "Acceso denegado" and stops propagation.
    """

    def __init__(self):
        self.settings = Settings()
        self.admin_ids = self.settings.admin_ids_list

    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Extract user from data (works for all event types in aiogram 3)
        user = data.get("event_from_user")

        # If we couldn't find a user, continue with the handler
        if not user:
            return await handler(event, data)

        user_id = user.id

        # Check if user is in admin list
        if user_id not in self.admin_ids:
            # If not admin, send access denied message and stop processing
            if hasattr(event, 'answer'):
                if isinstance(event, CallbackQuery):
                    await event.answer(ACCESS_DENIED_MESSAGE, show_alert=True)
                else:
                    await event.answer(ACCESS_DENIED_MESSAGE)
            else:
                # For other event types that don't have answer method
                pass

            # Simply return without calling the handler (stop propagation)
            return None

        # If admin, continue with handler
        return await handler(event, data)