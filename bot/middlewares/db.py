"""
Database session middleware for injecting AsyncSession into handlers.
Automatically handles commit/rollback and session closure.
"""
from typing import Callable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from bot.database.base import get_session


class DBSessionMiddleware(BaseMiddleware):
    """
    Middleware that injects a database session into the handler context
    and automatically handles session lifecycle (commit/rollback/close).
    """

    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Get a database session from the generator
        async for session in get_session():
            # Inject the session into the handler data
            data["session"] = session

            try:
                # Call the handler with the session in data
                result = await handler(event, data)

                # Commit the transaction if no exception occurred
                await session.commit()

                return result
            except Exception as e:
                # Rollback the transaction in case of an error
                await session.rollback()
                raise e