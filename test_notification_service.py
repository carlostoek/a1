"""
Test script to validate the NotificationService functionality using pytest.
"""
import pytest
from unittest.mock import AsyncMock, patch
from bot.services.notification_service import NotificationService


@pytest.mark.asyncio
async def test_send_valid_notification():
    """Test sending a valid notification."""
    # Create a mock bot instance
    mock_bot = AsyncMock()

    # Create the notification service
    notification_service = NotificationService(bot=mock_bot)

    # Send a valid notification
    result = await notification_service.send_notification(
        user_id=123456789,
        template_name="score_update",
        context_data={"points": 50, "total_points": 150}
    )

    # Assertions
    assert result is True
    mock_bot.send_message.assert_called_once()
    call_args = mock_bot.send_message.call_args
    assert call_args.kwargs.get('chat_id') == 123456789
    assert '50' in call_args.kwargs.get('text', '')


@pytest.mark.asyncio
async def test_fallback_unknown_template():
    """Test fallback behavior when using an unknown template."""
    # Create a mock bot instance
    mock_bot = AsyncMock()

    # Create the notification service
    notification_service = NotificationService(bot=mock_bot)

    # Send notification with unknown template
    result = await notification_service.send_notification(
        user_id=123456789,
        template_name="unknown_template",
        context_data={"points": 50, "total_points": 150}
    )

    # Assertions
    assert result is True
    mock_bot.send_message.assert_called_once()
    call_args = mock_bot.send_message.call_args
    text = call_args.kwargs.get('text', '')
    assert 'Error: Plantilla' in text
    assert 'unknown_template' in text


@pytest.mark.asyncio
async def test_missing_context_data():
    """Test behavior when context data is missing for template."""
    # Create a mock bot instance
    mock_bot = AsyncMock()

    # Create the notification service
    notification_service = NotificationService(bot=mock_bot)

    # Send notification with missing context data
    result = await notification_service.send_notification(
        user_id=123456789,
        template_name="score_update",
        context_data={"points": 50}  # Missing total_points
    )

    # Assertions
    assert result is True
    mock_bot.send_message.assert_called_once()
    call_args = mock_bot.send_message.call_args
    text = call_args.kwargs.get('text', '')
    assert 'Error de formato' in text


@pytest.mark.asyncio
async def test_error_handling_send_message_failure():
    """Test error handling when bot send_message fails."""
    # Create a mock bot instance
    mock_bot = AsyncMock()

    # Create the notification service
    notification_service = NotificationService(bot=mock_bot)

    # Mock send_message to raise an exception
    with patch.object(mock_bot, 'send_message', side_effect=Exception("Network error")):
        result = await notification_service.send_notification(
            user_id=123456789,
            template_name="score_update",
            context_data={"points": 50, "total_points": 150}
        )

        # Assertions
        assert result is False


@pytest.mark.asyncio
async def test_telegram_api_error_handling():
    """Test error handling when Telegram API error occurs."""
    from aiogram.exceptions import TelegramAPIError
    # Create a mock bot instance
    mock_bot = AsyncMock()

    # Create the notification service
    notification_service = NotificationService(bot=mock_bot)

    # Mock send_message to raise a TelegramAPIError
    with patch.object(mock_bot, 'send_message', side_effect=TelegramAPIError(method="sendMessage", message="Forbidden: bot was blocked by the user")):
        result = await notification_service.send_notification(
            user_id=123456789,
            template_name="score_update",
            context_data={"points": 50, "total_points": 150}
        )

        # Assertions
        assert result is False