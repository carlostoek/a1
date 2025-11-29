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
from bot.services.config_service import ConfigService
from bot.services.exceptions import ServiceError, SubscriptionError
from bot.states import SubscriptionTierStates


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


async def get_vip_menu_kb(session: AsyncSession):
    """Generate VIP menu keyboard with buttons for each active tier."""
    tiers = await ConfigService.get_all_tiers(session)
    keyboard = InlineKeyboardBuilder()

    if tiers:
        for tier in tiers:
            keyboard.button(
                text=f"🎟️ Generar Token ({tier.name})",
                callback_data=f"token_generate_{tier.id}"
            )
    else:
        # If no tiers, "Generar Token" is disabled.
        # A message will be shown in the handler.
        pass

    keyboard.button(text="Ver Stats", callback_data="vip_stats")
    keyboard.button(text="Configurar", callback_data="vip_config")
    keyboard.button(text="Volver", callback_data="admin_main_menu")
    keyboard.adjust(1)
    return keyboard.as_markup()


def get_free_menu_kb():
    """Generate Free menu keyboard with buttons: [Ver Stats, Configurar, Volver]"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Ver Stats", callback_data="free_stats")
    keyboard.button(text="Configurar", callback_data="free_config")
    keyboard.button(text="Volver", callback_data="admin_main_menu")
    keyboard.adjust(2)  # 2 buttons per row
    return keyboard.as_markup()


def get_config_menu_kb():
    """Generate Config menu keyboard with buttons: [Gestionar Tarifas, Volver]"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Gestionar Tarifas", callback_data="config_tiers")
    keyboard.button(text="Volver", callback_data="admin_main_menu")
    keyboard.adjust(1)
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
async def admin_vip(callback_query: CallbackQuery, session: AsyncSession):
    """Edit message to show VIP menu."""
    tiers = await ConfigService.get_all_tiers(session)
    text = "Menú VIP"
    if not tiers:
        text += "\n\n❌ No hay tarifas de suscripción activas. Por favor, configure una tarifa primero."
        
    await safe_edit_message(
        callback_query,
        text,
        reply_markup=await get_vip_menu_kb(session)
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
@admin_router.callback_query(F.data.startswith("token_generate_"))
async def generate_token_from_tier(callback_query: CallbackQuery, session: AsyncSession):
    """Generate a VIP token from a selected subscription tier."""
    try:
        tier_id = int(callback_query.data.split("_")[2])
        admin_id = callback_query.from_user.id

        # Generate the token link
        token_link = await SubscriptionService.generate_vip_token(
            session, admin_id, tier_id, callback_query.bot
        )
        
        tier = await ConfigService.get_tier_by_id(session, tier_id)

        response_text = (
            f"✅ Token VIP generado con éxito para la tarifa **{tier.name}**:\n\n"
            f"🔗 Link de invitación (copiar y enviar):\n"
            f"<code>{token_link}</code>"
        )
        await callback_query.message.answer(response_text)
        await callback_query.answer("Token generado.")

    except (SubscriptionError, ServiceError) as e:
        await callback_query.answer(f"Error: {e}", show_alert=True)
    except (IndexError, ValueError):
        await callback_query.answer("Error procesando la solicitud.", show_alert=True)


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

        await safe_edit_message(callback_query, stats_message, reply_markup=await get_vip_menu_kb(session))
    except ServiceError:
        await callback_query.answer('Ocurrió un error al obtener las estadísticas VIP.', show_alert=True)


@admin_router.callback_query(F.data == "vip_config")
async def vip_config(callback_query: CallbackQuery, session: AsyncSession):
    """Show VIP configuration options (to be implemented)."""
    await safe_edit_message(
        callback_query,
        "Configuración VIP\n(En desarrollo)",
        reply_markup=await get_vip_menu_kb(session)
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
    """Show general configuration options."""
    await safe_edit_message(
        callback_query,
        "Configuración General",
        reply_markup=get_config_menu_kb()
    )


@admin_router.callback_query(F.data == "config_tiers")
async def manage_tiers_menu(callback_query: CallbackQuery, session: AsyncSession):
    """Display a paginated list of all active subscription tiers."""
    tiers = await ConfigService.get_all_tiers(session)
    
    keyboard = InlineKeyboardBuilder()
    if not tiers:
        text = "No hay tarifas de suscripción configuradas."
    else:
        text = "Seleccione una tarifa para editar o elija una acción:"
        for tier in tiers:
            keyboard.button(
                text=f"🔹 {tier.name} (${tier.price_usd})",
                callback_data=f"tier_edit_{tier.id}"
            )
    
    keyboard.button(text="➕ Nueva Tarifa", callback_data="tier_new")
    keyboard.button(text="Volver", callback_data="admin_config")
    keyboard.adjust(1)

    await safe_edit_message(callback_query, text, reply_markup=keyboard.as_markup())


@admin_router.callback_query(F.data == "tier_new")
async def create_tier_start(callback_query: CallbackQuery, state: FSMContext):
    """Initiate the FSM flow to create a new subscription tier."""
    await state.set_state(SubscriptionTierStates.waiting_tier_name)
    await safe_edit_message(callback_query, "PASO 1/3: Introduce el nombre de la nueva tarifa (ej: 1 Mes Básico)")


@admin_router.message(SubscriptionTierStates.waiting_tier_name)
async def process_tier_name(message: Message, state: FSMContext):
    """Capture the tier name and ask for the duration."""
    await state.update_data(name=message.text)
    await state.set_state(SubscriptionTierStates.waiting_tier_duration)
    await message.answer("PASO 2/3: Introduce la duración en días (ej: 30)")


@admin_router.message(SubscriptionTierStates.waiting_tier_duration)
async def process_tier_duration(message: Message, state: FSMContext):
    """Capture the tier duration and ask for the price."""
    try:
        duration_days = int(message.text)
        await state.update_data(duration_days=duration_days)
        await state.set_state(SubscriptionTierStates.waiting_tier_price)
        await message.answer("PASO 3/3: Introduce el precio en USD (ej: 9.99)")
    except ValueError:
        await message.answer("Por favor, introduce un número válido para los días.")


@admin_router.message(SubscriptionTierStates.waiting_tier_price)
async def process_tier_price(message: Message, state: FSMContext, session: AsyncSession):
    """Capture the tier price, create the tier, and end the FSM flow."""
    try:
        price_usd = float(message.text)
        data = await state.get_data()
        
        await ConfigService.create_tier(
            session=session,
            name=data['name'],
            duration_days=data['duration_days'],
            price_usd=price_usd
        )
        
        await message.answer("✅ Tarifa creada con éxito.")
        await state.clear()
        
        # Fake a callback query to return to the tiers menu
        fake_callback_query = CallbackQuery(
            id="fake_callback", 
            from_user=message.from_user, 
            chat_instance="fake", 
            message=message, 
            data="config_tiers"
        )
        await manage_tiers_menu(fake_callback_query, session)

    except ValueError:
        await message.answer("Por favor, introduce un número válido para el precio (ej: 9.99).")
    except ServiceError as e:
        await message.answer(f"❌ Error al crear la tarifa: {e}")
        await state.clear()


@admin_router.callback_query(F.data.startswith("tier_edit_"))
async def edit_tier_select(callback_query: CallbackQuery, session: AsyncSession):
    """Display details of a selected tier and offer editing/deletion options."""
    tier_id = int(callback_query.data.split("_")[2])
    tier = await ConfigService.get_tier_by_id(session, tier_id)

    if not tier:
        await callback_query.answer("❌ Tarifa no encontrada.", show_alert=True)
        return

    text = (
        f"Editando Tarifa: **{tier.name}**\n\n"
        f"ID: `{tier.id}`\n"
        f"Duración: `{tier.duration_days}` días\n"
        f"Precio: `${tier.price_usd:.2f}`\n"
        f"Activa: `{'Sí' if tier.is_active else 'No'}`"
    )

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📝 Editar Nombre", callback_data=f"tier_edit_name_{tier.id}")
    keyboard.button(text="⏳ Editar Duración", callback_data=f"tier_edit_duration_{tier.id}")
    keyboard.button(text="💲 Editar Precio", callback_data=f"tier_edit_price_{tier.id}")
    keyboard.button(text="🗑️ Eliminar", callback_data=f"tier_delete_{tier.id}")
    keyboard.button(text="⬅️ Volver", callback_data="config_tiers")
    keyboard.adjust(1)
    
    await safe_edit_message(callback_query, text, reply_markup=keyboard.as_markup())
