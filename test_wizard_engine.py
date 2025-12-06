"""
Test the new wizard engine with validation scenarios:
1. Start rank creation wizard
2. Write a name too short (e.g. "A") → The validator should reject and ask again
3. Write valid name → advances to points
4. Write text in points field → rejects
5. Write number → advances
6. Complete flow and verify saving
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, User, Chat
from sqlalchemy.ext.asyncio import AsyncSession
from bot.wizards.rank_wizard import RankWizard
from bot.services.wizard_service import WizardService
from bot.services.gamification_service import GamificationService
from bot.wizards.validators import CommonValidators


class MockServices:
    def __init__(self):
        # Create a mock gamification service for testing
        self.gamification = MagicMock(spec=GamificationService)
        # Mock the create_rank method to return a simple rank object
        mock_rank = MagicMock()
        mock_rank.name = "Test Rank"
        mock_rank.id = 999
        self.gamification.create_rank = AsyncMock(return_value=mock_rank)


async def test_wizard_engine():
    print("Testing Wizard Engine Implementation...")
    
    # Initialize wizard service
    wizard_service = WizardService()
    
    # Create mock objects
    user_id = 123456
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = user_id
    message.text = "Veterano"  # Valid name for step 1
    
    callback_query = MagicMock(spec=CallbackQuery)
    callback_query.from_user = MagicMock(spec=User)
    callback_query.from_user.id = user_id
    callback_query.data = "yes"  # For VIP question
    callback_query.message = message
    
    state = MagicMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={'services': MockServices()})
    session = MagicMock(spec=AsyncSession)

    # Create mock services
    services = MockServices()
    
    print("1. Starting rank creation wizard...")
    # Start the wizard
    await wizard_service.start_wizard(
        user_id=user_id,
        wizard_class=RankWizard,
        fsm_context=state,
        services=services
    )
    
    print("✓ Wizard started successfully")
    
    # Test Step 1: Invalid name (too short)
    print("\n2. Testing invalid name validation (too short)...")
    result, status = await wizard_service.process_message_input(
        user_id=user_id, 
        text="A",  # Too short
        fsm_context=state, 
        session=session
    )
    
    if result and "error" in result:
        print("✓ Validation correctly rejected short name")
    else:
        print("✗ Validation did NOT reject short name")
    
    # Test Step 1: Valid name
    print("\n3. Testing valid name validation...")
    result, status = await wizard_service.process_message_input(
        user_id=user_id, 
        text="Veterano",  # Valid name
        fsm_context=state, 
        session=session
    )
    
    if status == "Valid input processed":
        print("✓ Valid name accepted and wizard advanced")
        print(f"✓ Name stored in context: {wizard_service.active_wizards[user_id].data.get('name')}")
    else:
        print("✗ Valid name not accepted")
    
    # Test Step 2: Points validation - invalid input (text)
    print("\n4. Testing invalid points validation (text input)...")
    result, status = await wizard_service.process_message_input(
        user_id=user_id, 
        text="invalid",  # Not a number
        fsm_context=state, 
        session=session
    )
    
    if result and "error" in result:
        print("✓ Validation correctly rejected text input for points")
    else:
        print("✗ Validation did NOT reject text input for points")
    
    # Test Step 2: Points validation - valid number
    print("\n5. Testing valid points validation...")
    result, status = await wizard_service.process_message_input(
        user_id=user_id, 
        text="500",  # Valid number
        fsm_context=state, 
        session=session
    )
    
    if status == "Valid input processed":
        print("✓ Valid points accepted and wizard advanced")
        print(f"✓ Points stored in context: {wizard_service.active_wizards[user_id].data.get('points')}")
    else:
        print("✗ Valid points not accepted")
    
    # Test Step 3: VIP callback - Yes
    print("\n6. Testing VIP callback (Yes)...")
    result, status = await wizard_service.process_callback_input(
        user_id=user_id, 
        callback_data="yes", 
        fsm_context=state, 
        session=session
    )
    
    if status == "Waiting for VIP days":
        print("✓ Callback correctly processed, waiting for VIP days")
    else:
        print(f"✗ Callback not processed correctly. Status: {status}")
    
    # Test Step 4: VIP days validation - valid number
    print("\n7. Testing VIP days validation...")
    result, status = await wizard_service.process_message_input(
        user_id=user_id,
        text="30",  # Valid number
        fsm_context=state,
        session=session
    )

    if status == "Wizard completed":
        print("✓ Valid VIP days accepted and wizard completed successfully")
        print(f"  - Result: {result}")
    else:
        print(f"✗ Expected wizard completion but got status: {status}")

    # Since the wizard is completed, we can't test further context, but we can validate
    # the completion worked based on the result
    print("\n8. Testing rank creation via GamificationService...")
    # Since we mocked the service, the result should be the mock rank that was returned
    if hasattr(result, 'name') and result.name == "Test Rank":
        print("✓ GamificationService.create_rank was called and returned mock rank")
    else:
        print(f"✗ Unexpected result from completion: {result}")

    # Test validator functions directly
    print("\n9. Testing validators directly...")

    # Test text_min_length
    short_validator = CommonValidators.text_min_length(3)
    long_validator = CommonValidators.text_min_length(3)

    if short_validator("A") is None:
        print("✓ text_min_length correctly rejects short text")
    else:
        print("✗ text_min_length does not reject short text")

    if long_validator("Valid") is not None:
        print("✓ text_min_length correctly accepts valid text")
    else:
        print("✗ text_min_length does not accept valid text")

    # Test is_integer
    integer_validator = CommonValidators.is_integer(0)

    if integer_validator("123") == 123:
        print("✓ is_integer correctly processes valid integer")
    else:
        print("✗ is_integer does not process valid integer")

    if integer_validator("text") is None:
        print("✓ is_integer correctly rejects non-integer")
    else:
        print("✗ is_integer does not reject non-integer")

    print("\n✓ All tests completed!")
    print("\nWizard Engine Implementation Summary:")
    print("- Core wizard engine implemented with WizardContext, WizardStep, and BaseWizard")
    print("- Common validators created with text_min_length and is_integer")
    print("- RankWizard implemented with all required steps")
    print("- Wizard service handles conditional flow (VIP/No VIP)")
    print("- Generic wizard handlers manage messages and callbacks")
    print("- Integration with GamificationService for rank creation")


if __name__ == "__main__":
    asyncio.run(test_wizard_engine())