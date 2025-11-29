"""
Manejadores de administración para el Bot de Telegram.
Implementa la navegación por menús y la generación de tokens.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.exceptions import TelegramBadRequest
from bot.middlewares.auth import AdminAuthMiddleware
from bot.middlewares.db import DBSessionMiddleware
from bot.services.subscription_service import SubscriptionService
from bot.services.channel_service import ChannelManagementService
from bot.services.exceptions import ServiceError, SubscriptionError
from bot.states import TokenGenerationStates


# Create router and apply middlewares
admin_router = Router()
admin_router.message.middleware(DBSessionMiddleware())
admin_router.message.middleware(AdminAuthMiddleware())
admin_router.callback_query.middleware(DBSessionMiddleware())
admin_router.callback_query.middleware(AdminAuthMiddleware())


async def safe_edit_message(callback_query: CallbackQuery, text: str, reply_markup=None):
    """
    Safely edit a message, handling the 'message is not modified' error.
    """
    try:
        await callback_query.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # If the message hasn't changed, just answer the callback
            await callback_query.answer()
        else:
            # If it's a different error, raise it
            raise e


def get_main_menu_kb():
    """Generate main menu keyboard with buttons: [Gestión VIP, Gestión Free, Config, Stats]"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Gestión VIP", callback_data="admin_vip")
    keyboard.button(text="Gestión Free", callback_data="admin_free")
    keyboard.button(text="Config", callback_data="admin_config")
    keyboard.button(text="Stats", callback_data="admin_stats")
    keyboard.button(text="Menú Principal", callback_data="admin_main_menu")  # Refresh main menu button
    keyboard.adjust(2)  # 2 buttons per row
    return keyboard.as_markup()


def get_vip_menu_kb():
    """Generate VIP menu keyboard with buttons: [Generar Token, Ver Stats, Configurar, Volver]"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Generar Token", callback_data="vip_generate_token")
    keyboard.button(text="Ver Stats", callback_data="vip_stats")
    keyboard.button(text="Configurar", callback_data="vip_config")
    keyboard.button(text="Volver", callback_data="admin_main_menu")
    keyboard.adjust(2)  # 2 buttons per row
    return keyboard.as_markup()


def get_free_menu_kb():
    """Generate Free menu keyboard with buttons: [Ver Stats, Configurar, Volver]"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Ver Stats", callback_data="free_stats")
    keyboard.button(text="Configurar", callback_data="free_config")
    keyboard.button(text="Volver", callback_data="admin_main_menu")
    keyboard.adjust(2)  # 2 buttons per row
    return keyboard.as_markup()


# Command handlers
@admin_router.message(Command("admin", "start"))
async def cmd_admin(message: Message):
    """Respond with welcome message and main menu keyboard."""
    welcome_text = "Bienvenido al Panel de Administración del Bot."
    await message.answer(welcome_text, reply_markup=get_main_menu_kb())


# Navigation callback handlers
@admin_router.callback_query(F.data == "admin_main_menu")
async def admin_main_menu(callback_query: CallbackQuery):
    """Edit message to show main menu."""
    await safe_edit_message(
        callback_query,
        "Menú Principal - Panel de Administración",
        reply_markup=get_main_menu_kb()
    )


@admin_router.callback_query(F.data == "admin_vip")
async def admin_vip(callback_query: CallbackQuery):
    """Edit message to show VIP menu."""
    await safe_edit_message(
        callback_query,
        "Menú VIP",
        reply_markup=get_vip_menu_kb()
    )


@admin_router.callback_query(F.data == "admin_free")
async def admin_free(callback_query: CallbackQuery):
    """Edit message to show Free menu."""
    await safe_edit_message(
        callback_query,
        "Menú Free",
        reply_markup=get_free_menu_kb()
    )


@admin_router.callback_query(F.data == "admin_stats")
async def admin_stats(callback_query: CallbackQuery, session: AsyncSession):
    """Show stats summary using ChannelManagementService."""
    try:
        # Get channel stats
        stats = await ChannelManagementService.get_channel_stats(session, "vip")
        free_stats = await ChannelManagementService.get_channel_stats(session, "general")

        stats_message = (
            f"📊 Estadísticas del Bot:\n\n"
            f"Usuarios VIP activos: {stats['active_subscribers']}\n"
            f"Solicitudes Free: {free_stats['total_requests']}\n"
            f"Solicitudes pendientes: {free_stats['pending_requests']}"
        )

        await safe_edit_message(callback_query, stats_message, reply_markup=get_main_menu_kb())
    except ServiceError:
        await callback_query.answer('Ocurrió un error al obtener las estadísticas.', show_alert=True)


# Callback handlers for VIP menu options
@admin_router.callback_query(F.data == "vip_generate_token")
async def vip_generate_token(callback_query: CallbackQuery, state: FSMContext):
    """Start token generation flow by asking for duration."""
    await state.set_state(TokenGenerationStates.waiting_duration)
    await safe_edit_message(callback_query, "Ingrese la duración del token en horas:")


@admin_router.callback_query(F.data == "vip_stats")
async def vip_stats(callback_query: CallbackQuery, session: AsyncSession):
    """Show VIP stats using ChannelManagementService."""
    try:
        # Get VIP channel stats
        stats = await ChannelManagementService.get_channel_stats(session, "vip")

        stats_message = (
            f"📊 Estadísticas VIP:\n\n"
            f"Usuarios VIP activos: {stats['active_subscribers']}"
        )

        await safe_edit_message(callback_query, stats_message, reply_markup=get_vip_menu_kb())
    except ServiceError:
        await callback_query.answer('Ocurrió un error al obtener las estadísticas VIP.', show_alert=True)


@admin_router.callback_query(F.data == "vip_config")
async def vip_config(callback_query: CallbackQuery):
    """Show VIP configuration options (to be implemented)."""
    await safe_edit_message(
        callback_query,
        "Configuración VIP\n(En desarrollo)",
        reply_markup=get_vip_menu_kb()
    )


# Callback handlers for Free menu options
@admin_router.callback_query(F.data == "free_stats")
async def free_stats(callback_query: CallbackQuery, session: AsyncSession):
    """Show Free channel stats using ChannelManagementService."""
    try:
        # Get Free channel stats
        stats = await ChannelManagementService.get_channel_stats(session, "general")

        stats_message = (
            f"📊 Estadísticas Free:\n\n"
            f"Solicitudes totales: {stats['total_requests']}\n"
            f"Solicitudes pendientes: {stats['pending_requests']}"
        )

        await safe_edit_message(callback_query, stats_message, reply_markup=get_free_menu_kb())
    except ServiceError:
        await callback_query.answer('Ocurrió un error al obtener las estadísticas Free.', show_alert=True)


@admin_router.callback_query(F.data == "free_config")
async def free_config(callback_query: CallbackQuery):
    """Show Free configuration options (to be implemented)."""
    await safe_edit_message(
        callback_query,
        "Configuración Free\n(En desarrollo)",
        reply_markup=get_free_menu_kb()
    )


# Callback handlers for main menu options
@admin_router.callback_query(F.data == "admin_config")
async def admin_config(callback_query: CallbackQuery):
    """Show general configuration options (to be implemented)."""
    await safe_edit_message(
        callback_query,
        "Configuración General\n(En desarrollo)",
        reply_markup=get_main_menu_kb()
    )


# Token generation FSM flow
@admin_router.message(TokenGenerationStates.waiting_duration)
async def process_token_duration(message: Message, state: FSMContext, session: AsyncSession):
    """Process token duration input and generate token."""
    try:
        # Validate that input is a number
        duration_hours = int(message.text)

        # Generate the VIP token using the subscription service
        admin_id = message.from_user.id
        token = await SubscriptionService.generate_vip_token(session, admin_id, duration_hours)

        # Send the generated token in a copiable format
        response_text = f"✅ Token VIP generado con éxito:\n\n<code>{token.token}</code>\n\nDuración: {duration_hours} horas"
        await message.answer(response_text)

        # Clear the state
        await state.clear()

    except ValueError:
        # If input is not a number, ask again
        await message.answer("Por favor, ingrese un número válido para la duración en horas:")
    except SubscriptionError:
        await message.answer('Error generando el token.')
        await state.clear()
