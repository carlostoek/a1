from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.wizard_service import WizardService, WizardStates


router = Router()
wizard_service = WizardService()


def _create_completion_message(result):
    """Helper to create completion messages."""
    if hasattr(result, 'name'):
        return f"✅ Rango '{result.name}' creado exitosamente!"
    elif isinstance(result, dict) and 'name' in result:
        return f"✅ Rango '{result['name']}' creado exitosamente!"
    else:
        return "✅ Proceso completado exitosamente!"


def _handle_completion_response(response, message_func, edit_func):
    """Helper to handle completion responses based on the type of interaction."""
    if hasattr(response, 'name'):
        completion_msg = f"✅ Rango '{response.name}' creado exitosamente!"
    elif isinstance(response, dict) and 'name' in response:
        completion_msg = f"✅ Rango '{response['name']}' creado exitosamente!"
    else:
        completion_msg = "✅ Proceso completado exitosamente!"

    return completion_msg


async def _handle_error_for_user_id(user_id, state, wizard_service, error_message):
    """Helper to handle errors by cleaning up state and notifying user."""
    if user_id in wizard_service.active_wizards:
        del wizard_service.active_wizards[user_id]
    await state.clear()
    return error_message


@router.message(F.state == WizardStates.active)
async def handle_wizard_message(message: Message, state: FSMContext, session: AsyncSession):
    """Captura todo texto cuando hay un wizard activo y lo pasa a WizardService.process_message_input."""
    user_id = message.from_user.id
    text = message.text

    try:
        result, status = await wizard_service.process_message_input(user_id, text, state, session)

        if result:
            if status == "Wizard completed":
                # If the wizard has completed, result might be the created rank
                completion_msg = _handle_completion_response(result, message.answer, lambda text: None)
                await message.answer(completion_msg)
            else:
                if "error" in result:
                    await message.answer(result["error"])

                # Send the current step's text
                await message.answer(result["text"], reply_markup=result.get("keyboard"))
    except Exception as e:
        # Clean up wizard state on error
        error_msg = await _handle_error_for_user_id(user_id, state, wizard_service,
                                                   "❌ Ocurrió un error durante el proceso. Por favor, intenta de nuevo.")
        await message.answer(error_msg)


@router.callback_query(F.state == WizardStates.active)
async def handle_wizard_callback(callback_query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Captura botones del wizard (Sí/No/Saltar)."""
    user_id = callback_query.from_user.id
    callback_data = callback_query.data

    try:
        # Use the wizard service's method to handle callback
        result, status = await wizard_service.process_callback_input(user_id, callback_data, state, session)

        if result:
            if status == "Wizard completed":
                # If the wizard has completed, result might be the created rank
                completion_msg = _handle_completion_response(result, lambda text: None,
                                                            callback_query.message.edit_text)
                await callback_query.message.edit_text(completion_msg)
            elif status in ["Waiting for VIP days", "Moved to next step"]:
                # If waiting for VIP days or moved to next step, send the message with keyboard
                await callback_query.message.edit_text(
                    result["text"],
                    reply_markup=result.get("keyboard")
                )
            else:
                # Handle other status messages
                await callback_query.answer("Error en el proceso", show_alert=True)

        await callback_query.answer()  # Always answer the callback
    except Exception as e:
        # Clean up wizard state on error
        error_msg = await _handle_error_for_user_id(user_id, state, wizard_service,
                                                   "❌ Error en el proceso. Por favor, intenta de nuevo.")
        await callback_query.answer(error_msg, show_alert=True)