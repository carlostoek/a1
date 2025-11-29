"""
Admin authentication middleware to check if user is authorized.
"""
from typing import Callable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from bot.config import Settings


class AdminAuthMiddleware(BaseMiddleware):
    """
    Middleware that checks if the user is in the admin list.
    If not an admin, sends "Acceso denegado" and stops propagation.
    """

    def __init__(self):
        self.settings = Settings()

    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Extract user ID depending on event type
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

        # If we couldn't find a user ID, continue with handler
        if user_id is None:
            return await handler(event, data)

        # Check if user is in admin list
        admin_ids = self.settings.admin_ids_list

        if user_id not in admin_ids:
            # If not admin, send access denied message and stop processing
            if isinstance(event, Message):
                await event.answer("Acceso denegado")
            elif isinstance(event, CallbackQuery):
                await event.answer("Acceso denegado", show_alert=True)

            # Simply return without calling the handler (stop propagation)
            return None

        # If admin, continue with handler
        return await handler(event, data)