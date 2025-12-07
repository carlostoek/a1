import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, User
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


@pytest.mark.asyncio
async def test_wizard_engine():
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

    # 1. Starting rank creation wizard
    await wizard_service.start_wizard(
        user_id=user_id,
        wizard_class=RankWizard,
        fsm_context=state,
        services=services
    )

    # Verify wizard started successfully (no exception thrown)
    assert user_id in wizard_service.active_wizards

    # 2. Testing invalid name validation (too short)
    result, status = await wizard_service.process_message_input(
        user_id=user_id,
        text="A",  # Too short
        fsm_context=state,
        session=session
    )

    assert result is not None and "error" in result

    # 3. Testing valid name validation
    result, status = await wizard_service.process_message_input(
        user_id=user_id,
        text="Veterano",  # Valid name with min 3 chars
        fsm_context=state,
        session=session
    )

    assert status == "Valid input processed"
    assert wizard_service.active_wizards[user_id].data.get('name') == 'Veterano'

    # 4. Testing invalid points validation (text input)
    result, status = await wizard_service.process_message_input(
        user_id=user_id,
        text="invalid",  # Not a number
        fsm_context=state,
        session=session
    )

    assert result is not None and "error" in result

    # 5. Testing valid points validation
    result, status = await wizard_service.process_message_input(
        user_id=user_id,
        text="500",  # Valid number
        fsm_context=state,
        session=session
    )

    assert status == "Valid input processed"
    assert wizard_service.active_wizards[user_id].data.get('points') == 500

    # 6. Testing VIP callback - Yes
    result, status = await wizard_service.process_callback_input(
        user_id=user_id,
        callback_data="yes",
        fsm_context=state,
        session=session
    )

    assert status == "Waiting for VIP days"

    # 7. Testing VIP days validation - valid number
    # Since the next step after entering VIP days would complete the wizard,
    # we expect "Wizard completed" status
    result, status = await wizard_service.process_message_input(
        user_id=user_id,
        text="30",  # Valid number
        fsm_context=state,
        session=session
    )

    assert status == "Wizard completed"

    # 8. Testing rank creation via GamificationService
    # Since we mocked the service, the result should be the mock rank that was returned
    assert hasattr(result, 'name') and result.name == "Test Rank"

    # 9. Testing validators directly
    # Test text_min_length
    short_validator = CommonValidators.text_min_length(3)
    long_validator = CommonValidators.text_min_length(3)

    assert short_validator("A") is None  # Should reject short text
    assert long_validator("Valid") is not None  # Should accept valid text

    # Test is_integer
    integer_validator = CommonValidators.is_integer(0)

    assert integer_validator("123") == 123  # Should process valid integer
    assert integer_validator("text") is None  # Should reject non-integer


def test_validator_functions():
    # Additional tests for validator functions
    short_validator = CommonValidators.text_min_length(3)
    assert short_validator("A") is None  # Too short
    assert short_validator("AB") is None  # Still too short
    assert short_validator("ABC") is not None  # Minimum length
    assert short_validator("ABCD") is not None  # Above minimum

    integer_validator = CommonValidators.is_integer(0)
    assert integer_validator("123") == 123
    assert integer_validator("0") == 0
    assert integer_validator("-5") is None  # Negative if min_val is 0
    assert integer_validator("text") is None
    assert integer_validator("") is None