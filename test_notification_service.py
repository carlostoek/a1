"""
Test script to validate the NotificationService functionality.
"""
import asyncio
from unittest.mock import AsyncMock, patch
from bot.services.notification_service import NotificationService


async def test_notification_service():
    """Test the NotificationService functionality."""
    
    # Create a mock bot instance
    mock_bot = AsyncMock()
    
    # Create the notification service
    notification_service = NotificationService(bot=mock_bot)
    
    print("Testing NotificationService...")
    
    # Test 1: Send a valid notification
    try:
        result = await notification_service.send_notification(
            user_id=123456789,
            template_name="score_update",
            context_data={"points": 50, "total_points": 150}
        )
        print(f"✓ Test 1 - Valid notification: {result}")
        # Check that send_message was called with correct parameters
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        print(f"  - Called with chat_id: {call_args.kwargs.get('chat_id')}")
        print(f"  - Text contains: {'points' in call_args.kwargs.get('text', '')}")
        mock_bot.send_message.reset_mock()  # Reset for next test
    except Exception as e:
        print(f"✗ Test 1 - Valid notification failed: {e}")
    
    # Test 2: Send notification with unknown template (should use fallback)
    try:
        result = await notification_service.send_notification(
            user_id=123456789,
            template_name="unknown_template",
            context_data={"points": 50, "total_points": 150}
        )
        print(f"✓ Test 2 - Unknown template fallback: {result}")
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        print(f"  - Fallback message used: {'Error: Plantilla' in call_args.kwargs.get('text', '')}")
        mock_bot.send_message.reset_mock()
    except Exception as e:
        print(f"✗ Test 2 - Unknown template fallback failed: {e}")
    
    # Test 3: Send notification with missing context data
    try:
        result = await notification_service.send_notification(
            user_id=123456789,
            template_name="score_update",
            context_data={"points": 50}  # Missing total_points
        )
        print(f"✓ Test 3 - Missing context data: {result}")
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        text = call_args.kwargs.get('text', '')
        print(f"  - Error message generated: {'Error de formato' in text}")
        mock_bot.send_message.reset_mock()
    except Exception as e:
        print(f"✗ Test 3 - Missing context data failed: {e}")
    
    # Test 4: Error handling when bot send_message fails
    try:
        # Mock send_message to raise an exception
        with patch.object(mock_bot, 'send_message', side_effect=Exception("Network error")):
            result = await notification_service.send_notification(
                user_id=123456789,
                template_name="score_update",
                context_data={"points": 50, "total_points": 150}
            )
            print(f"✓ Test 4 - Error handling: {result}")
            print(f"  - Returns False on error: {result is False}")
    except Exception as e:
        print(f"✗ Test 4 - Error handling failed: {e}")
    
    print("\nNotificationService tests completed!")


if __name__ == "__main__":
    asyncio.run(test_notification_service())