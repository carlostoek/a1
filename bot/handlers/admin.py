"""
Manejadores de administración para el Bot de Telegram.
Implementa la navegación por menús y la generación de tokens.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.exceptions import TelegramBadRequest
from bot.middlewares.auth import AdminAuthMiddleware
from bot.middlewares.db import DBSessionMiddleware
from bot.services.subscription_service import SubscriptionService
from bot.services.channel_service import ChannelManagementService
from bot.services.config_service import ConfigService
from bot.services.exceptions import ServiceError, SubscriptionError
from bot.states import SubscriptionTierStates, ChannelSetupStates, FreeConfigStates, ReactionSetupStates
from bot.config import Settings
from datetime import datetime, timedelta, timezone
from bot.utils.ui import MenuFactory

# Create router and apply middlewares
admin_router = Router()
admin_router.message.middleware(DBSessionMiddleware())
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
    keyboard.button(text="⚙️ Configurar Canales", callback_data="config_channels_menu")
    keyboard.button(text="Volver", callback_data="admin_main_menu")
    keyboard.adjust(1)
    return keyboard.as_markup()


def get_channels_config_kb():
    """Generate channels config menu keyboard with buttons: [Canal VIP, Canal Free, Volver]"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Canal VIP", callback_data="setup_vip_select")
    keyboard.button(text="Canal Free", callback_data="setup_free_select")
    keyboard.button(text="Volver", callback_data="admin_config")
    keyboard.adjust(1)
    return keyboard.as_markup()


# Command handlers
@admin_router.message(Command("admin", "start"))
async def cmd_admin(message: Message, command: CommandObject, session: AsyncSession):
    """
    Handle the /start and /admin commands.
    - If /start has a token, redeem it.
    - If /start has no token, show a welcome message.
    - If /admin is used by an admin, show the admin menu.
    """
    user_id = message.from_user.id
    token_str = command.args

    # User role check
    settings = Settings()
    is_admin = user_id in settings.admin_ids_list

    if token_str:
        # Token redemption flow
        try:
            result = await SubscriptionService.redeem_token(session, user_id, token_str)

            if result["success"]:
                tier = result["tier"]
                await SubscriptionService.send_token_redemption_success(message, tier, session)
            else:
                await message.reply(f"❌ Error al canjear el token: {result['error']}")

        except SubscriptionError as e:
            await message.reply(f"❌ Ocurrió un error inesperado: {e}")

    elif is_admin:
        # Admin menu flow
        welcome_text = "Bienvenido al Panel de Administración del Bot."

        # Use MenuFactory for consistency
        main_options = [
            ("💎 Gestión VIP", "admin_vip"),
            ("🆓 Gestión Free", "admin_free"),
            ("⚙️ Configuración", "admin_config"),
            ("📊 Estadísticas", "admin_stats"),
        ]

        menu_data = MenuFactory.create_menu(
            title="Menú Principal de Administración",
            options=main_options,
            description=welcome_text,  # Use welcome text as description
            back_callback=None,  # Command start doesn't have back button
            has_main=False   # Command start doesn't have main button (it IS the main)
        )

        await message.answer(menu_data['text'], reply_markup=menu_data['markup'])

    else:
        # Generic user welcome
        await message.reply(
            "👋 ¡Bienvenido! Si tienes un token de invitación, úsalo con el comando `/start TOKEN`.\n"
            "Si buscas acceso gratuito, usa el comando `/free`."
        )


# Navigation callback handlers
@admin_router.callback_query(F.data == "admin_main_menu")
async def admin_main_menu(callback_query: CallbackQuery):
    """Edit message to show main menu using MenuFactory."""
    # Define main menu options
    main_options = [
        ("💎 Gestión VIP", "admin_vip"),
        ("🆓 Gestión Free", "admin_free"),
        ("⚙️ Configuración", "admin_config"),
        ("📊 Estadísticas", "admin_stats"),
    ]

    # Generate menu using factory
    menu_data = MenuFactory.create_menu(
        title="Menú Principal de Administración",
        options=main_options,
        back_callback=None,  # Main menu doesn't have back button
        has_main=False   # Main menu doesn't have main button
    )

    await safe_edit_message(
        callback_query,
        menu_data['text'],
        menu_data['markup']
    )

@admin_router.callback_query(F.data == "admin_vip")
async def admin_vip(callback_query: CallbackQuery, session: AsyncSession):
    """Edit message to show VIP menu using MenuFactory."""
    tiers = await ConfigService.get_all_tiers(session)

    # Build VIP menu options using list comprehension
    options = [
        (f"🎟️ Generar Token ({tier.name})", f"token_generate_{tier.id}")
        for tier in tiers
    ]

    # Add additional VIP options
    options.extend([
        ("📊 Ver Stats", "vip_stats"),
        ("⚙️ Configurar", "vip_config"),
    ])

    # Check if there are no tiers and add appropriate description
    description = None
    if not tiers:
        description = "❌ No hay tarifas de suscripción activas. Por favor, configure una tarifa primero."

    menu_data = MenuFactory.create_menu(
        title="Menú VIP",
        options=options,
        description=description,
        back_callback="admin_main_menu",
        has_main=True
    )

    await safe_edit_message(
        callback_query,
        menu_data['text'],
        menu_data['markup']
    )

@admin_router.callback_query(F.data == "admin_free")
async def admin_free(callback_query: CallbackQuery):
    """Edit message to show Free menu using MenuFactory."""
    # Define free menu options
    free_options = [
        ("📊 Ver Stats", "free_stats"),
        ("⚙️ Configurar", "free_config"),
    ]

    menu_data = MenuFactory.create_menu(
        title="Menú Free",
        options=free_options,
        back_callback="admin_main_menu",
        has_main=True
    )

    await safe_edit_message(
        callback_query,
        menu_data['text'],
        menu_data['markup']
    )

@admin_router.callback_query(F.data == "admin_stats")
async def admin_stats(callback_query: CallbackQuery, session: AsyncSession):
    """Show stats summary using ChannelManagementService and MenuFactory."""
    try:
        # Get channel stats
        stats = await ChannelManagementService.get_channel_stats(session, "vip")
        free_stats = await ChannelManagementService.get_channel_stats(session, "general")

        # Create stats info as description
        stats_description = (
            f"📊 Estadísticas del Bot:\n\n"
            f"Usuarios VIP activos: {stats['active_subscribers']}\n"
            f"Solicitudes Free: {free_stats['total_requests']}\n"
            f"Solicitudes pendientes: {free_stats['pending_requests']}"
        )

        # Create simple menu with just navigation options
        stats_options = [
            ("🔄 Actualizar", "admin_stats"),  # Refresh stats
        ]

        menu_data = MenuFactory.create_menu(
            title="Estadísticas",
            options=stats_options,
            description=stats_description,
            back_callback="admin_main_menu",
            has_main=True
        )

        await safe_edit_message(callback_query, menu_data['text'], menu_data['markup'])
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
async def free_config(callback_query: CallbackQuery, session: AsyncSession):
    """Show Free configuration options."""
    config = await ConfigService.get_bot_config(session)
    current_wait_time = config.wait_time_minutes

    text = f"Configuración Free\n\nTiempo de espera actual: {current_wait_time} minutos"

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="⏱️ Configurar Tiempo de Espera", callback_data="free_wait_time_config")
    keyboard.button(text="Volver", callback_data="admin_free")
    keyboard.adjust(1)

    await safe_edit_message(
        callback_query,
        text,
        reply_markup=keyboard.as_markup()
    )


# Callback handlers for free configuration
@admin_router.callback_query(F.data == "free_wait_time_config")
async def start_free_wait_time_config(callback_query: CallbackQuery, state: FSMContext):
    """Start the FSM flow to configure free channel wait time."""
    await state.set_state(FreeConfigStates.waiting_wait_time_minutes)
    await safe_edit_message(
        callback_query,
        "⏱️ Configuración de Tiempo de Espera\n\n"
        "Por favor, introduce el tiempo de espera en minutos (ej: 60, 1440 para 1 día, 10080 para 1 semana):"
    )


# Message handler for wait time input
@admin_router.message(FreeConfigStates.waiting_wait_time_minutes)
async def process_free_wait_time(message: Message, state: FSMContext, session: AsyncSession):
    """Process the wait time input and update the configuration."""
    # Manual admin authentication check
    user_id = message.from_user.id
    settings = Settings()
    if user_id not in settings.admin_ids_list:
        await message.reply("Acceso denegado")
        return

    try:
        wait_time_minutes = int(message.text)

        if wait_time_minutes < 0:
            await message.reply("❌ El tiempo de espera no puede ser negativo. Introduce un valor positivo en minutos.")
            return

        # Update the configuration in the database
        updated_config = await ConfigService.update_config(
            session,
            "wait_time_minutes",
            wait_time_minutes
        )

        # Clear the FSM state
        await state.clear()

        # Confirm the update to the admin
        await message.reply(f"✅ Tiempo de espera actualizado a {wait_time_minutes} minutos.")

    except ValueError:
        await message.reply("❌ Por favor, introduce un número válido de minutos (ej: 60, 1440, 10080).")
    except Exception as e:
        # Escape special characters in the error message to avoid Telegram parsing issues
        error_msg = str(e).replace('<', '\\<').replace('>', '\\>')
        await message.reply(f"❌ Error al actualizar la configuración: {error_msg}")
        await state.clear()


# Callback handlers for main menu options
@admin_router.callback_query(F.data == "admin_config")
async def admin_config(callback_query: CallbackQuery):
    """Show general configuration options using MenuFactory."""
    # Define configuration menu options
    config_options = [
        ("💳 Gestionar Tarifas", "config_tiers"),
        ("⚙️ Configurar Canales", "config_channels_menu"),
    ]

    menu_data = MenuFactory.create_menu(
        title="Configuración General",
        options=config_options,
        back_callback="admin_main_menu",
        has_main=True
    )

    await safe_edit_message(
        callback_query,
        menu_data['text'],
        menu_data['markup']
    )


@admin_router.callback_query(F.data == "vip_config")
async def admin_vip_config(callback_query: CallbackQuery):
    """Show VIP configuration options using MenuFactory."""
    # Define VIP configuration options
    vip_config_options = [
        ("📊 Ver Stats", "vip_stats"),
        ("💄 Configurar Reacciones", "vip_config_reactions"),
    ]

    menu_data = MenuFactory.create_menu(
        title="Configuración VIP",
        options=vip_config_options,
        back_callback="admin_vip",
        has_main=True
    )

    await safe_edit_message(
        callback_query,
        menu_data['text'],
        menu_data['markup']
    )


@admin_router.callback_query(F.data == "free_config")
async def admin_free_config(callback_query: CallbackQuery):
    """Show Free configuration options using MenuFactory."""
    # Define Free configuration options
    free_config_options = [
        ("📊 Ver Stats", "free_stats"),
        ("💄 Configurar Reacciones", "free_config_reactions"),
        ("⏱️ Configurar Tiempo de Espera", "free_wait_time_config"),
    ]

    menu_data = MenuFactory.create_menu(
        title="Configuración Free",
        options=free_config_options,
        back_callback="admin_free",
        has_main=True
    )

    await safe_edit_message(
        callback_query,
        menu_data['text'],
        menu_data['markup']
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

        # Vuelve a mostrar el menú de tarifas enviando un nuevo mensaje.
        tiers = await ConfigService.get_all_tiers(session)

        keyboard = InlineKeyboardBuilder()
        if not tiers:
            text = "No hay tarifas de suscripción configuradas."
        else:
            text = "Seleccione una tarifa para editar o elija una acción:"
            for tier in tiers:
                keyboard.button(
                    text=f"🔹 {tier.name} (${tier.price_usd:.2f})",
                    callback_data=f"tier_edit_{tier.id}"
                )

        keyboard.button(text="➕ Nueva Tarifa", callback_data="tier_new")
        keyboard.button(text="Volver", callback_data="admin_config")
        keyboard.adjust(1)

        await message.answer(text, reply_markup=keyboard.as_markup())

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


# Callback handlers for reaction configuration
@admin_router.callback_query(F.data == "vip_config_reactions")
async def setup_reactions_start_vip(callback_query: CallbackQuery, state: FSMContext):
    """Start the reaction setup flow for VIP channel."""
    # Store the channel type in FSM context
    await state.update_data(channel_type="vip")

    # Set the state to wait for reactions input
    await state.set_state(ReactionSetupStates.waiting_reactions_input)

    # Respond with instructions using safe_edit_message
    instructions = (f"💋 Configuración de Reacciones Inline VIP\n"
                   f"Envía la lista de emojis permitidos separados por coma (ej: 👍, 🔥, 🚀). "
                   f"Se usarán como botones de interacción en las publicaciones.")

    await safe_edit_message(
        callback_query,
        instructions,
        reply_markup=None  # No additional buttons for this message
    )


@admin_router.callback_query(F.data == "free_config_reactions")
async def setup_reactions_start_free(callback_query: CallbackQuery, state: FSMContext):
    """Start the reaction setup flow for Free channel."""
    # Store the channel type in FSM context
    await state.update_data(channel_type="free")

    # Set the state to wait for reactions input
    await state.set_state(ReactionSetupStates.waiting_reactions_input)

    # Respond with instructions using safe_edit_message
    instructions = (f"💋 Configuración de Reacciones Inline Free\n"
                   f"Envía la lista de emojis permitidos separados por coma (ej: 👍, 🔥, 🚀). "
                   f"Se usarán como botones de interacción en las publicaciones.")

    await safe_edit_message(
        callback_query,
        instructions,
        reply_markup=None  # No additional buttons for this message
    )


# Message handler for processing reactions input
@admin_router.message(ReactionSetupStates.waiting_reactions_input)
async def process_reactions_input(message: Message, state: FSMContext, session: AsyncSession):
    """Process the input of reaction emojis."""
    # Manual admin authentication check
    user_id = message.from_user.id
    settings = Settings()
    if user_id not in settings.admin_ids_list:
        await message.reply("Acceso denegado")
        return

    # Get the channel type from FSM data
    data = await state.get_data()
    channel_type = data.get("channel_type", "unknown")

    if not channel_type or channel_type not in ["vip", "free"]:
        await message.reply("❌ Error interno. No se pudo determinar el tipo de canal. Por favor, intenta de nuevo.")
        await state.clear()
        return

    # Call the ConfigService to save reactions
    result = await ConfigService.setup_reactions(
        channel_type=channel_type,
        reactions_str=message.text,
        session=session
    )

    if result["success"]:
        # Success: show list of reactions that were saved
        reactions_list = result["reactions"]
        response_text = f"✅ Reacciones guardadas. Lista: {', '.join(reactions_list)}."
        await message.reply(response_text)

        # Clear the state
        await state.clear()

        # Return to the corresponding configuration menu
        if channel_type == "vip":
            await admin_vip(message, session)
        else:  # free
            await admin_free(message)
    else:
        # Error: show error message
        error = result["error"]
        await message.reply(f"❌ Error al guardar reacciones: {error}")

        # Clear the state
        await state.clear()


# Callback handlers for channel configuration
@admin_router.callback_query(F.data == "config_channels_menu")
async def config_channels_menu(callback_query: CallbackQuery):
    """Display channel configuration menu using MenuFactory."""
    # Define channel configuration options
    channel_options = [
        ("Canal VIP", "setup_vip_select"),
        ("Canal Free", "setup_free_select"),
    ]

    menu_data = MenuFactory.create_menu(
        title="Configuración de Canales",
        options=channel_options,
        back_callback="admin_config",  # Go back to config menu
        has_main=True
    )

    await safe_edit_message(
        callback_query,
        menu_data['text'],
        menu_data['markup']
    )


@admin_router.callback_query(F.data.startswith("setup_"))
async def setup_channel_start(callback_query: CallbackQuery, state: FSMContext):
    """Start the channel setup flow based on the type (VIP or Free)."""
    # Extract the channel type from callback data
    callback_data = callback_query.data
    if callback_data == "setup_vip_select":
        channel_type = "vip"
        type_name = "VIP"
    elif callback_data == "setup_free_select":
        channel_type = "free"
        type_name = "Free"
    else:
        await callback_query.answer("Error: Tipo de canal no reconocido", show_alert=True)
        return

    # Store the channel type in FSM context
    await state.update_data(channel_type=channel_type)

    # Set the state to wait for the channel ID or forwarded message
    await state.set_state(ChannelSetupStates.waiting_channel_id_or_forward)

    # Respond with instructions
    instructions = f"✅ Modo de Configuración de Canal {type_name}\nPor favor, envía una de estas dos opciones:\n * El ID numérico del canal (ej: -10012345678).\n * Reenvía un mensaje de ese canal a este chat.\n   Asegúrate de que el bot ya es administrador del canal."
    await safe_edit_message(callback_query, instructions)


# Message handler for channel ID or forwarded message
@admin_router.message(ChannelSetupStates.waiting_channel_id_or_forward)
async def process_channel_input(message: Message, state: FSMContext, session: AsyncSession):
    """Process channel ID input (either manual ID or forwarded message)."""
    # Manual admin authentication check
    user_id = message.from_user.id
    settings = Settings()
    if user_id not in settings.admin_ids_list:
        await message.reply("Acceso denegado")
        return

    # Get the channel type from FSM data
    data = await state.get_data()
    channel_type = data.get("channel_type")
    if not channel_type:
        await message.reply("❌ Error interno. No se pudo determinar el tipo de canal. Por favor, intenta de nuevo desde el menú de configuración.")
        await state.clear()
        return

    channel_id = None

    # Extract ID from forwarded message or from text
    if message.forward_from_chat:
        # Channel ID from forwarded message
        channel_id = message.forward_from_chat.id
    else:
        # Assume user sent the numeric ID directly
        try:
            channel_id = int(message.text)
        except (ValueError, TypeError):
            await message.reply("❌ Error al registrar el canal. Razón: Formato de ID inválido. Por favor, envía un ID numérico válido (ej: -10012345678) o reenvía un mensaje del canal.")
            return

    # Call the ChannelManagementService to register the channel ID
    result = await ChannelManagementService.register_channel_id(
        channel_type=channel_type,
        raw_id=channel_id,
        bot=message.bot,
        session=session
    )

    if result["success"]:
        type_name = "VIP" if channel_type == "vip" else "Free"
        response_text = f"🎉 Canal {type_name} registrado con ID: {result['channel_id']}. ¡Configuración guardada!"
        await message.reply(response_text)
    else:
        await message.reply(f"❌ Error al registrar el canal. Razón: {result['error']}. ¿El bot es administrador en ese canal?")

    # Clear the state
    await state.clear()
