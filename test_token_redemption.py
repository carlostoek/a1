"""
Test script for user token redemption functionality.
"""
import asyncio
from bot.services.subscription_service import SubscriptionService
from bot.database.base import get_session


async def test_redeem_token():
    """Test the token redemption functionality."""
    print("Testing token redemption functionality...")
    
    # Get a session
    async for session in get_session():
        # First create a test token
        admin_id = 123456
        duration_hours = 24
        from bot.database.models import InvitationToken
        import uuid
        from datetime import datetime, timezone
        
        # Create a test token
        token_str = str(uuid.uuid4())
        token = InvitationToken(
            token=token_str,
            generated_by=admin_id,
            duration_hours=duration_hours
        )
        session.add(token)
        await session.commit()
        await session.refresh(token)
        
        print(f"Created test token: {token_str}")
        
        # Now try to redeem this token
        user_id = 987654
        result = await SubscriptionService.redeem_token(session, user_id, token_str)
        
        print(f"Redemption result: {result}")
        
        if result["success"]:
            print("✅ Token redemption successful!")
            print(f"Duration: {result['duration']} hours")
            print(f"Expiry: {result['expiry']}")
        else:
            print(f"❌ Token redemption failed: {result['error']}")
        
        # Try to redeem the same token again (should fail)
        result2 = await SubscriptionService.redeem_token(session, user_id+1, token_str)
        print(f"Second redemption attempt (should fail): {result2}")
        
        break  # Exit the generator after one iteration


if __name__ == "__main__":
    asyncio.run(test_redeem_token())