from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.wizard_service import WizardService
from bot.database.session import async_session


router = Router()
wizard_service = WizardService()


@router.message(F.state == "wizard_active")
async def handle_wizard_message(message: Message, state: FSMContext, session: AsyncSession):
    """Captura todo texto cuando hay un wizard activo y lo pasa a WizardService.process_message_input."""
    user_id = message.from_user.id
    text = message.text

    result, status = await wizard_service.process_message_input(user_id, text, state, session)

    if result:
        if status == "Wizard completed":
            # If the wizard has completed, result might be the created rank
            if hasattr(result, 'name'):
                await message.answer(f"✅ Rango '{result.name}' creado exitosamente!")
            elif isinstance(result, dict) and 'name' in result:
                await message.answer(f"✅ Rango '{result['name']}' creado exitosamente!")
            else:
                await message.answer("✅ Proceso completado exitosamente!")
        else:
            if "error" in result:
                await message.answer(result["error"])

            # Send the current step's text
            await message.answer(result["text"], reply_markup=result.get("keyboard"))


@router.callback_query(F.state == "wizard_active")
async def handle_wizard_callback(callback_query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Captura botones del wizard (Sí/No/Saltar)."""
    user_id = callback_query.from_user.id
    callback_data = callback_query.data

    # Use the wizard service's method to handle callback
    result, status = await wizard_service.process_callback_input(user_id, callback_data, state, session)

    if result:
        if status == "Wizard completed":
            # If the wizard has completed, result might be the created rank
            if hasattr(result, 'name'):
                await callback_query.message.edit_text(f"✅ Rango '{result.name}' creado exitosamente!")
            elif isinstance(result, dict) and 'name' in result:
                await callback_query.message.edit_text(f"✅ Rango '{result['name']}' creado exitosamente!")
            else:
                await callback_query.message.edit_text("✅ Proceso completado exitosamente!")
        elif status == "Waiting for VIP days":
            # If waiting for VIP days, send the message with keyboard
            await callback_query.message.edit_text(
                result["text"],
                reply_markup=result.get("keyboard")
            )
        elif status == "Moved to next step":
            # If moved to next step after skipping VIP days, send the message with keyboard
            await callback_query.message.edit_text(
                result["text"],
                reply_markup=result.get("keyboard")
            )
        else:
            # Handle other status messages
            await callback_query.answer("Error en el proceso", show_alert=True)

    await callback_query.answer()  # Always answer the callback