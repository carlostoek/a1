"""
Manejadores de administración para el Bot de Telegram.
Implementa la navegación por menús y la generación de tokens.
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from aiogram.exceptions import TelegramBadRequest
from bot.middlewares.auth import AdminAuthMiddleware
from bot.middlewares.db import DBSessionMiddleware
from bot.services.subscription_service import SubscriptionService
from bot.services.channel_service import ChannelManagementService
from bot.services.config_service import ConfigService
from bot.services.stats_service import StatsService
from bot.services.dependency_injection import Services
from bot.services.exceptions import ServiceError, SubscriptionError
from bot.services.event_bus import Events
from bot.database.models import RewardContentFile, RewardContentPack
from bot.states import SubscriptionTierStates, ChannelSetupStates, PostSendingStates, ReactionSetupStates, WaitTimeSetupStates, ContentPackCreationStates, RankConfigStates
from bot.config import Settings
from datetime import datetime, timedelta, timezone
from bot.utils.ui import MenuFactory, ReactionCallback, escape_markdownv2_text

# Constants
SUBSCRIBER_PAGE_SIZE = 5

# Create router and apply middlewares
admin_router = Router()
admin_router.message.middleware(DBSessionMiddleware())
admin_router.callback_query.middleware(DBSessionMiddleware())
admin_router.callback_query.middleware(AdminAuthMiddleware())

async def safe_edit_message(callback_query: CallbackQuery, text: str, reply_markup=None):
    """
    Safely edit a message, handling the 'message is not modified' error.
    """
    escaped_text = escape_markdownv2_text(text)
    try:
        await callback_query.message.edit_text(escaped_text, reply_markup=reply_markup, parse_mode="MarkdownV2")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # If the message hasn't changed, just answer the callback
            await callback_query.answer()
        else:
            # If it's a different error, raise it
            raise e

async def safe_send_message(message_obj: Message, text: str, reply_markup=None):
    """
    Safely send a message with proper MarkdownV2 escaping.
    """
    escaped_text = escape_markdownv2_text(text)
    return await message_obj.reply(escaped_text, reply_markup=reply_markup, parse_mode="MarkdownV2")

async def safe_send_direct(bot: Bot, chat_id: int, text: str, reply_markup=None):
    """
    Safely send a direct message with proper MarkdownV2 escaping.
    """
    escaped_text = escape_markdownv2_text(text)
    return await bot.send_message(chat_id, escaped_text, reply_markup=reply_markup, parse_mode="MarkdownV2")

async def safe_callback_answer(callback_query: CallbackQuery, text: str, show_alert: bool = False):
    """
    Safely answer a callback query with proper MarkdownV2 escaping (if needed).
    """
    escaped_text = escape_markdownv2_text(text)
    await callback_query.answer(escaped_text, show_alert=show_alert)

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
async def cmd_admin(message: Message, command: CommandObject, session: AsyncSession, services: Services):
    """
    Handle the /start and /admin commands.
    - If /start has a token, redeem it.
    - If /start has a referral link (ref_...), process it.
    - If /start has no token, show a welcome message.
    - If /admin is used by an admin, show the admin menu.
    """
    user_id = message.from_user.id
    args = command.args

    # Split args to handle referral links
    payload = None
    token_str = None
    referral_payload = None

    if args:
        # Check if it's a referral link
        if args.startswith("ref_"):
            referral_payload = args
        # Otherwise, treat as a token (whether it starts with "token_" or not)
        else:
            token_str = args

    # User role check
    settings = Settings()
    is_admin = user_id in settings.admin_ids_list

    # First, process referral if present
    if referral_payload:
        # Process referral - independently of token redemption success
        await services.gamification.process_referral(user_id, referral_payload, session)

    if token_str:
        # Token redemption flow
        try:
            result = await SubscriptionService.redeem_token(session, user_id, token_str)

            if result["success"]:
                tier = result["tier"]
                await SubscriptionService.send_token_redemption_success(message, tier, session)
            else:
                await safe_send_message(message, f"❌ Error al canjear el token: {result['error']}")

        except SubscriptionError as e:
            await safe_send_message(message, f"❌ Ocurrió un error inesperado: {e}")

    elif is_admin:
        # Admin menu flow - use the same dynamic channel naming as the callback handler
        main_options = await get_main_menu_options(message.bot, session)

        welcome_text = "Bienvenido al Panel de Administración del Bot."

        # Use MenuFactory for consistency
        menu_data = MenuFactory.create_menu(
            title="Panel de Control A1",
            options=main_options,
            description=welcome_text,  # Use welcome text as description
            back_callback=None,  # Command start doesn't have back button
            has_main=False   # Command start doesn't have main button (it IS the main)
        )

        await message.answer(menu_data['text'], reply_markup=menu_data['markup'], parse_mode="MarkdownV2")

    else:
        # Generic user welcome
        await message.reply(
            "👋 ¡Bienvenido! Si tienes un token de invitación, úsalo con el comando `/start TOKEN`.\n"
            "Si buscas acceso gratuito, usa el comando `/free`."
        )


@admin_router.message(Command("help"))
async def cmd_help(message: Message):
    """
    Show a list of available commands for administrators.
    """
    user_id = message.from_user.id
    settings = Settings()
    is_admin = user_id in settings.admin_ids_list

    if not is_admin:
        await message.reply("❌ Acceso denegado. Solo para administradores.")
        return

    help_text = (
        "📋 <b>COMANDOS DISPONIBLES</b>\n\n"

        "<b>COMANDOS DE ADMINISTRADOR:</b>\n"
        "• <code>/admin</code> - Acceder al panel de administración\n"
        "• <code>/start</code> - Iniciar el bot (menú administrador si eres admin)\n"
        "• <code>/help</code> - Mostrar este mensaje de ayuda\n\n"

        "<b>COMANDOS DE USUARIO:</b>\n"
        "• <code>/daily</code> - Reclamar recompensa diaria\n\n"

        "<b>FUNCIONALIDADES DEL SISTEMA:</b>\n"
        "• Sistema de suscripciones VIP y tokens\n"
        "• Gestión de canales (VIP y Gratuitos)\n"
        "• Sistema de gamificación con puntos y rangos\n"
        "• Envío de publicaciones con reacciones\n"
        "• Sistema de recompensas automáticas\n"
        "• Estadísticas y análisis avanzado\n"
        "• Event Bus para comunicación entre módulos\n"
        "• Sistema de recompensa diaria (streaks)\n"
    )

    await message.answer(help_text, parse_mode="HTML")


# Navigation callback handlers
async def get_main_menu_options(bot, session: AsyncSession):
    """
    Helper function to generate main menu options with dynamic channel names.

    Args:
        bot: Bot instance to get channel info
        session: Database session to get config

    Returns:
        List of tuples containing (text, callback_data) for menu options
    """
    # Get the bot configuration to check if channels are configured
    config = await ConfigService.get_bot_config(session)

    # Get channel information for VIP and Free channels
    # Default button text (without bold formatting for buttons as they don't support it)
    vip_menu_text = "💎 Gestión VIP"
    free_menu_text = "💬 Gestión Free"

    # Try to get the actual channel names if configured
    if config.vip_channel_id:
        try:
            # Get channel info from Telegram using the bot
            chat = await bot.get_chat(chat_id=config.vip_channel_id)
            # Use the channel title if available, otherwise use the ID
            channel_name = chat.title if chat.title else f"VIP-{config.vip_channel_id}"
            vip_menu_text = f"💎 {channel_name}"
        except Exception:
            # If there's an error getting the channel info, just show the configured status
            vip_menu_text = f"💎 VIP Configurado"

    if config.free_channel_id:
        try:
            # Get channel info from Telegram using the bot
            chat = await bot.get_chat(chat_id=config.free_channel_id)
            # Use the channel title if available, otherwise use the ID
            channel_name = chat.title if chat.title else f"Free-{config.free_channel_id}"
            free_menu_text = f"💬 {channel_name}"
        except Exception:
            # If there's an error getting the channel info, just show the configured status
            free_menu_text = f"💬 Free Configurado"

    # Define main menu options according to specification
    main_options = [
        (vip_menu_text, "admin_vip"),
        (free_menu_text, "admin_free"),
        ("📊 Centro de Reportes", "admin_stats"),
        ("⚙️ Diagnóstico y Config", "admin_config"),
    ]

    return main_options


@admin_router.callback_query(F.data == "admin_main_menu")
async def admin_main_menu(callback_query: CallbackQuery, session: AsyncSession, services: Services):
    """Edit message to show main menu using MenuFactory."""
    # Get main menu options with dynamic channel names
    main_options = await get_main_menu_options(callback_query.bot, session)

    # Generate menu using factory
    menu_data = MenuFactory.create_menu(
        title="Panel de Control A1",
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

    # Get the bot configuration to get channel info
    config = await ConfigService.get_bot_config(session)

    # Set the title based on whether channel is configured
    title = "DASHBOARD VIP"
    if config.vip_channel_id:
        try:
            # Get channel info from Telegram using the bot
            chat = await callback_query.bot.get_chat(chat_id=config.vip_channel_id)
            # Use the channel title if available, otherwise use the ID
            channel_name = chat.title if chat.title else f"VIP Channel"
            title = f"DASHBOARD {channel_name}"
        except Exception:
            # If there's an error getting the channel info, just show the configured status
            title = f"DASHBOARD VIP (Configurado)"

    # Build VIP menu options according to specification with sections
    options = [
        # -- ACCIONES RÁPIDAS --
        ("📝 Enviar Post (con Reacciones)", "admin_send_channel_post"),
        ("🔑 Generar Token", "vip_generate_token"),

        # -- GESTIÓN --
        ("👥 Base de Suscriptores (Paginado)", "vip_manage"),
        ("💰 Tarifas y Precios", "vip_config_tiers"),

        # -- CONFIGURACIÓN TÉCNICA --
        ("💋 Reacciones y Puntos", "vip_config_reactions"),
        ("🛡️ Protección de Contenido", "vip_toggle_protection"),  # New feature
        ("⚙️ Vincular ID Canal", "setup_vip_select"),

        # -- RECOMPENSAS --
        ("🏆 Rangos", "vip_manage_ranks"),
        ("🎁 Packs de Recompensas", "admin_content_packs"),
    ]

    # Check if there are no tiers and add appropriate description
    description = None
    if not tiers:
        description = "❌ No hay tarifas de suscripción activas. Por favor, configure una tarifa primero."

    menu_data = MenuFactory.create_menu(
        title=title,
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
async def admin_free(callback_query: CallbackQuery, session: AsyncSession):
    """Edit message to show Free menu using MenuFactory."""
    # Get the bot configuration to get channel info
    config = await ConfigService.get_bot_config(session)

    # Set the title based on whether channel is configured
    title = "DASHBOARD FREE"
    if config.free_channel_id:
        try:
            # Get channel info from Telegram using the bot
            chat = await callback_query.bot.get_chat(chat_id=config.free_channel_id)
            # Use the channel title if available, otherwise use the ID
            channel_name = chat.title if chat.title else f"Free Channel"
            title = f"DASHBOARD {channel_name}"
        except Exception:
            # If there's an error getting the channel info, just show the configured status
            title = f"DASHBOARD FREE (Configurado)"

    # Definir opciones del menú FREE según especificación con secciones
    free_options = [
        # -- SALA DE ESPERA --
        ("⚡ Procesar Cola Ahora", "process_pending_now"),
        ("🧹 Limpiar Solicitudes", "cleanup_old_requests"),  # Recuperado del Sistema A
        ("⏰ Config Tiempo Espera", "set_wait_time"),

        # -- CONTENIDO --
        ("📝 Enviar Post Free", "send_to_free_channel"),

        # -- CONFIGURACIÓN TÉCNICA --
        ("💋 Reacciones y Puntos", "free_config_reactions"),
        ("🛡️ Protección de Contenido", "free_toggle_protection"),  # Nuevo
        ("⚙️ Vincular ID Canal", "setup_free_select"),
    ]

    menu_data = MenuFactory.create_menu(
        title=title,
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
async def admin_stats_menu(callback_query: CallbackQuery, session: AsyncSession):
    """Show main statistics menu with specified options."""
    # Create the main stats menu with specified options
    stats_options = [
        ("📊 Resumen General", "stats_general"),
        ("💎 Métricas VIP", "stats_vip"),
        ("💬 Métricas Free", "stats_free"),
    ]

    menu_data = MenuFactory.create_menu(
        title="CENTRO DE REPORTES",
        options=stats_options,
        back_callback="admin_main_menu",
        has_main=True
    )

    await safe_edit_message(
        callback_query,
        menu_data['text'],
        menu_data['markup']
    )


@admin_router.callback_query(F.data == "stats_general")
async def view_general_stats(callback_query: CallbackQuery, session: AsyncSession):
    """Show general statistics for the bot."""
    try:
        # Get general stats from the service
        stats = await StatsService.get_general_stats(session)

        # Format the summary text as specified
        text = (
            "📊 **ESTADÍSTICAS GENERALES DEL BOT**\n\n"
            "👤 **USUARIOS Y SUSCRIPCIONES**\n"
            f"- Total de Usuarios Únicos: {stats['total_users']}\n"
            f"- Suscripciones VIP Activas: {stats['active_vip']}\n"
            f"- Suscripciones VIP Históricas (Exp./Rev.): {stats['expired_revoked_vip']}\n"
            f"- Tokens de Invitación Generados: {stats['tokens_generated']}\n\n"
            "💰 **INGRESOS (Placeholder)**\n"
            f"- Ingresos Totales Estimados: {stats['total_revenue']} (Se implementará con pasarela de pago)"
        )

        # Create keyboard with back button to stats menu
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="↩️ Volver a Estadísticas", callback_data="admin_stats")

        await safe_edit_message(
            callback_query,
            text,
            reply_markup=keyboard.as_markup()
        )
    except ServiceError as e:
        # Log the error for debugging: logger.error(f"Error al obtener estadísticas generales: {e}")
        await callback_query.answer("Ocurrió un error al obtener las estadísticas generales.", show_alert=True)


@admin_router.callback_query(F.data == "stats_vip")
async def view_vip_stats(callback_query: CallbackQuery, session: AsyncSession):
    """Show VIP subscription statistics."""
    try:
        # Get VIP stats from the service
        stats = await StatsService.get_vip_stats(session)

        # Format the tier counts in a more readable way
        tier_info = ""
        if stats['tier_counts']:
            for tier_id, count in stats['tier_counts'].items():
                tier_info += f"- Tier {tier_id}: {count} usuarios\n"
        else:
            tier_info = "- No hay suscriptores activos\n"

        # Format the summary text as specified
        text = (
            "💎 **ESTADÍSTICAS VIP**\n\n"
            "📈 **DISTRIBUCIÓN POR TARIFA**\n"
            f"{tier_info}\n"
            "🎫 **TOKENS DE INVITACIÓN**\n"
            f"- Tokens Redimidos: {stats['tokens_redeemed']}\n"
            f"- Tokens Expirados/Sin Usar: {stats['tokens_expired_unused']}"
        )

        # Create keyboard with back button to stats menu
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="↩️ Volver a Estadísticas", callback_data="admin_stats")

        await safe_edit_message(
            callback_query,
            text,
            reply_markup=keyboard.as_markup()
        )
    except ServiceError as e:
        # Log the error for debugging: logger.error(f"Error al obtener estadísticas VIP: {e}")
        await callback_query.answer("Ocurrió un error al obtener las estadísticas VIP.", show_alert=True)


@admin_router.callback_query(F.data == "stats_free")
async def view_free_stats(callback_query: CallbackQuery, session: AsyncSession):
    """Show free channel statistics."""
    try:
        # Get free channel stats from the service
        stats = await StatsService.get_free_channel_stats(session)

        # Format the summary text as specified
        text = (
            "💬 **ESTADÍSTICAS CANAL FREE**\n\n"
            "⏳ **SOLICITUDES EN ESPERA (Waiting Room)**\n"
            f"- Solicitudes Pendientes: {stats['pending_count']}\n"
            f"- Solicitudes Procesadas (Histórico): {stats['processed_count']}\n"
            f"- Solicitudes Rechazadas/Limpiadas: {stats['rejected_count']}"
        )

        # Create keyboard with back button to stats menu
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="↩️ Volver a Estadísticas", callback_data="admin_stats")

        await safe_edit_message(
            callback_query,
            text,
            reply_markup=keyboard.as_markup()
        )
    except ServiceError as e:
        # Log the error for debugging: logger.error(f"Error al obtener estadísticas FREE: {e}")
        await callback_query.answer("Ocurrió un error al obtener las estadísticas FREE.", show_alert=True)


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


# Callback handlers for wait time configuration
@admin_router.callback_query(F.data == "free_wait_time_config")
async def set_wait_time_start(callback_query: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Start the FSM flow to configure free channel wait time."""
    # Get current wait time value
    config = await ConfigService.get_bot_config(session)
    current_value = config.wait_time_minutes

    # Set the state to wait for the new time
    await state.set_state(WaitTimeSetupStates.waiting_wait_time_minutes)

    # Send message with current value and instructions
    instructions = (f"⏰ Configuración de Tiempo de Espera Free\n"
                   f"El valor actual es: {current_value} minutos.\n"
                   f"Por favor, envía la nueva duración de la espera en minutos (solo números enteros).")

    await safe_edit_message(
        callback_query,
        instructions
    )


# Message handler for process wait time input
@admin_router.message(WaitTimeSetupStates.waiting_wait_time_minutes)
async def process_wait_time_input(message: Message, state: FSMContext, session: AsyncSession):
    """Process the wait time input and update the configuration."""
    # Manual admin authentication check
    user_id = message.from_user.id
    settings = Settings()
    if user_id not in settings.admin_ids_list:
        await message.reply("Acceso denegado")
        return

    # Call the ConfigService to update wait time
    result = await ConfigService.update_wait_time(message.text, session)

    if result["success"]:
        # Success: show new value
        new_value = result["wait_time_minutes"]
        response_text = f"✅ Tiempo de espera actualizado a {new_value} minutos. Las nuevas solicitudes lo usarán inmediatamente."
        await safe_send_message(message, response_text)

        # Acknowledge completion after success
        await safe_send_message(message, "Regresando al menú principal para continuar.")
    else:
        # Error: show specific error message from service
        error = result["error"]
        response_text = f"❌ {error}"
        await safe_send_message(message, response_text)

    # Clear the state
    await state.clear()


# Callback handlers for post sending
@admin_router.callback_query(F.data.in_(["admin_send_channel_post", "send_to_free_channel"]))
async def setup_post_start(callback_query: CallbackQuery, state: FSMContext):
    """Start the post sending flow for VIP or Free channel."""
    # Determine channel type based on callback data
    if callback_query.data == "admin_send_channel_post":
        channel_type = "vip"
        message_text = (
            "📡 Enviando publicación al Canal VIP\n\n"
            "Por favor, envía el contenido que deseas publicar (texto, foto, video, etc.)."
        )
    else:  # send_to_free_channel
        channel_type = "free"
        message_text = (
            "📡 Enviando publicación al Canal Free\n\n"
            "Por favor, envía el contenido que deseas publicar (texto, foto, video, etc.)."
        )

    # Store channel type in FSM context
    await state.update_data(channel_type=channel_type)
    await state.set_state(PostSendingStates.waiting_post_content)
    await safe_edit_message(
        callback_query,
        message_text
    )


@admin_router.message(PostSendingStates.waiting_post_content)
async def receive_post_content(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    """Receive post content and check if reactions are configured."""
    # Store the message ID and chat ID in FSM
    await state.update_data(message_id=message.message_id, from_chat_id=message.chat.id)

    # Get channel type from FSM
    data = await state.get_data()
    channel_type = data.get("channel_type")
    if not channel_type:
        await message.reply("❌ Error: No se pudo determinar el canal de destino. Por favor, inicia el proceso de nuevo.")
        await state.clear()
        return

    # Get reactions list for the channel type using shared method
    reactions_list = await ConfigService.get_reactions_for_channel(session, channel_type)

    # Bifurcation based on whether reactions are configured
    if reactions_list and len(reactions_list) > 0:
        # CASE A: Reactions are configured, ask for decision
        await state.set_state(PostSendingStates.waiting_reaction_decision)

        # Create inline keyboard with reaction decision options
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="✅ Sí", callback_data="post_react_yes")
        keyboard.button(text="❌ No", callback_data="post_react_no")
        keyboard.adjust(2)  # 2 buttons per row

        await safe_send_message(
            message,
            "💋 Reacciones Detectadas\n¿Deseas añadir los botones de reacción a esta publicación?",
            reply_markup=keyboard.as_markup()
        )
    else:
        # CASE B: No reactions configured, skip to confirmation
        await state.update_data(use_reactions=False)
        # Continue to preview generation
        await generate_preview(message, state, session, bot)


@admin_router.callback_query(F.data.in_(["post_react_yes", "post_react_no"]), PostSendingStates.waiting_reaction_decision)
async def process_reaction_decision(callback_query: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    """Process the reaction decision and proceed to preview."""
    await state.update_data(use_reactions=(callback_query.data == "post_react_yes"))

    # Proceed to generate preview
    await state.set_state(PostSendingStates.waiting_confirmation)
    await generate_preview(callback_query, state, session, bot)


async def generate_preview(context, state: FSMContext, session: AsyncSession, bot: Bot):
    """Generate a preview of the post with or without reactions."""
    # Get all necessary data from FSM
    data = await state.get_data()
    message_id = data.get("message_id")
    from_chat_id = data.get("from_chat_id")
    use_reactions = data.get("use_reactions", False)
    channel_type = data.get("channel_type")

    if not all((message_id, from_chat_id, channel_type)):
        # We can't use callback_query here since this function can be called from message handlers
        # So we'll send an error message to the chat instead
        error_msg = "❌ Error: La sesión ha expirado. Por favor, inicia el proceso de nuevo."
        try:
            if isinstance(context, CallbackQuery):
                await context.answer(error_msg, show_alert=True)
            else:
                await context.reply(error_msg)
        except:
            # If sending message fails, just return
            pass
        await state.clear()
        return

    # Prepare the reply markup based on use_reactions flag
    reply_markup = None
    if use_reactions:
        # Get reactions list for the channel type using shared method
        reactions_list = await ConfigService.get_reactions_for_channel(session, channel_type)

        if reactions_list:
            reply_markup = MenuFactory.create_reaction_keyboard(channel_type, reactions_list)

    # Send preview to the admin (current chat)
    if isinstance(context, CallbackQuery):
        admin_chat_id = context.message.chat.id
    else:  # Assumes Message type
        admin_chat_id = context.chat.id

    try:
        # Copy the message to the admin as a preview
        await bot.copy_message(
            chat_id=admin_chat_id,
            from_chat_id=from_chat_id,
            message_id=message_id,
            reply_markup=reply_markup
        )
    except TelegramBadRequest as e:
        # If we can't copy the message, we need to handle it differently
        # For now, let's just send a text message for preview
        preview_text = f"No se pudo generar la previsualización ({e}). Mensaje ID {message_id} de chat {from_chat_id}"
        await bot.send_message(admin_chat_id, preview_text)

    # Send confirmation menu
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🚀 Enviar", callback_data="confirm_send")
    keyboard.button(text="❌ Cancelar", callback_data="cancel_send")
    keyboard.adjust(2)

    await safe_send_direct(
        bot,
        admin_chat_id,
        "¿Enviar esta publicación?",
        reply_markup=keyboard.as_markup()
    )


@admin_router.callback_query(F.data == "confirm_send")
async def confirm_post_send(callback_query: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    """Confirm and send the post to the target channel."""
    # Get all necessary data from FSM
    data = await state.get_data()
    message_id = data["message_id"]
    from_chat_id = data["from_chat_id"]
    use_reactions = data.get("use_reactions", False)
    channel_type = data["channel_type"]

    # Call the ChannelManagementService to broadcast the post
    result = await ChannelManagementService.broadcast_post(
        target_channel_type=channel_type,
        message_id=message_id,
        from_chat_id=from_chat_id,
        use_reactions=use_reactions,
        bot=bot,
        session=session
    )

    if result["success"]:
        await callback_query.answer(f"✅ Publicación enviada al canal {channel_type}!", show_alert=True)
    else:
        await callback_query.answer(f"❌ Error al enviar la publicación: {result['error']}", show_alert=True)

    # Clear the state
    await state.clear()


@admin_router.callback_query(F.data == "cancel_send")
async def cancel_post_send(callback_query: CallbackQuery, state: FSMContext):
    """Cancel the post sending process."""
    await callback_query.answer("❌ Envió de publicación cancelado.", show_alert=True)
    await state.clear()


@admin_router.callback_query(F.data == "vip_toggle_protection")
async def vip_toggle_content_protection(callback_query: CallbackQuery, session: AsyncSession, services: Services):
    """Toggle content protection for VIP channel."""
    try:
        # Get current protection status using service container
        current_status = await services.config.get_content_protection_status(session, "vip")

        # Toggle protection status
        new_status = not current_status
        result = await services.config.toggle_content_protection(session, "vip", new_status)

        if result["success"]:
            status_text = "activada" if new_status else "desactivada"
            await callback_query.answer(f"✅ Protección de contenido VIP {status_text}", show_alert=True)

            # Refresh the menu to show current state
            await admin_vip(callback_query, session)
        else:
            await callback_query.answer(f"❌ Error: {result['error']}", show_alert=True)
    except (ServiceError, SQLAlchemyError) as e:
        await callback_query.answer(f"❌ Error al cambiar protección VIP: {str(e)}", show_alert=True)
    except Exception as e:
        await callback_query.answer(f"❌ Error inesperado al cambiar protección VIP: {str(e)}", show_alert=True)


@admin_router.callback_query(F.data == "free_toggle_protection")
async def free_toggle_content_protection(callback_query: CallbackQuery, session: AsyncSession, services: Services):
    """Toggle content protection for Free channel."""
    try:
        # Get current protection status using service container
        current_status = await services.config.get_content_protection_status(session, "free")

        # Toggle protection status
        new_status = not current_status
        result = await services.config.toggle_content_protection(session, "free", new_status)

        if result["success"]:
            status_text = "activada" if new_status else "desactivada"
            await callback_query.answer(f"✅ Protección de contenido Free {status_text}", show_alert=True)

            # Refresh the menu to show current state
            await admin_free(callback_query)
        else:
            await callback_query.answer(f"❌ Error: {result['error']}", show_alert=True)
    except (ServiceError, SQLAlchemyError) as e:
        await callback_query.answer(f"❌ Error al cambiar protección Free: {str(e)}", show_alert=True)
    except Exception as e:
        await callback_query.answer(f"❌ Error inesperado al cambiar protección Free: {str(e)}", show_alert=True)


@admin_router.callback_query(F.data == "process_pending_now")
async def process_pending_requests_now(callback_query: CallbackQuery, session: AsyncSession, bot: Bot):
    """Manually trigger the processing of all pending free channel requests."""
    try:
        # Process all pending requests using the service method
        result = await ChannelManagementService.process_pending_requests(session, bot)

        if result["success"]:
            # Display the result message showing how many were processed
            await callback_query.answer(result["message"], show_alert=True)
        else:
            # Display error message if the operation failed
            await callback_query.answer(f"❌ Error al procesar solicitudes: {result['error']}", show_alert=True)
    except (ServiceError, SQLAlchemyError) as e:
        await callback_query.answer(f"❌ Error al procesar solicitudes pendientes: {str(e)}", show_alert=True)
    except Exception as e:
        await callback_query.answer(f"❌ Error inesperado al procesar solicitudes pendientes: {str(e)}", show_alert=True)


@admin_router.callback_query(F.data == "cleanup_old_requests")
async def cleanup_old_requests(callback_query: CallbackQuery, session: AsyncSession, services: Services):
    """Manually clean up old free channel requests."""
    try:
        result = await services.channel_manager.cleanup_old_requests(session)

        if result["success"]:
            await callback_query.answer(result["message"], show_alert=True)
        else:
            await callback_query.answer(f"❌ Error al limpiar solicitudes: {result['error']}", show_alert=True)
    except (ServiceError, SQLAlchemyError) as e:
        await callback_query.answer(f"❌ Error al limpiar solicitudes: {str(e)}", show_alert=True)
    except Exception as e:
        await callback_query.answer(f"❌ Error inesperado al limpiar solicitudes: {str(e)}", show_alert=True)


# Callback handlers for VIP subscriber management
@admin_router.callback_query(F.data == "vip_manage")
async def view_subscribers_list_first_page(callback_query: CallbackQuery, session: AsyncSession, bot: Bot):
    """Display first page of active VIP subscribers."""
    await view_subscribers_list(callback_query, session, bot, page=1)


@admin_router.callback_query(F.data.regexp(r"vip_page_\d+"))
async def view_subscribers_list_page(callback_query: CallbackQuery, session: AsyncSession, bot: Bot):
    """Display specific page of active VIP subscribers."""
    # Extract page number from callback data
    try:
        page = int(callback_query.data.split("_")[2])
    except (ValueError, IndexError):
        page = 1
    await view_subscribers_list(callback_query, session, bot, page=page)


async def view_subscribers_list(callback_query: CallbackQuery, session: AsyncSession, bot: Bot, page: int = 1):
    """Display paginated list of active VIP subscribers."""
    # Parse page number from callback data if needed - this is now passed as parameter

    # Use constant page size
    PAGE_SIZE = SUBSCRIBER_PAGE_SIZE

    # Get paginated list of active VIPs
    users, total_count = await SubscriptionService.get_active_vips_paginated(page, PAGE_SIZE, session)

    # Calculate total pages
    total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE if total_count > 0 else 1

    # Build the menu with user list
    text = f"**GESTIÓN DE SUSCRIPTORES VIP**\n\n"
    text += f"Total suscriptores activos: {total_count}\n\n"

    if users:
        for user in users:
            expiry_date = user.expiry_date.strftime("%d/%m/%Y %H:%M")
            text += f"👤 ID: {user.user_id} | 📅 Vence: {expiry_date}\n"
            text += f"   (Registrado: {user.join_date.strftime('%d/%m/%Y')})\n\n"
    else:
        text += "❌ No hay suscriptores VIP activos en esta página.\n\n"

    # Create keyboard with user details buttons and pagination
    keyboard = InlineKeyboardBuilder()

    # Add buttons for each user
    for user in users:
        expiry_date = user.expiry_date.strftime("%d/%m")
        keyboard.button(text=f"👤 {user.user_id} | 📅 {expiry_date}", callback_data=f"vip_user_detail_{user.user_id}_{page}")

    # Add pagination controls
    pagination_buttons = MenuFactory.create_pagination_keyboard(page, total_pages, "vip_page")
    for button in pagination_buttons:
        keyboard.add(button)

    # Add back button
    keyboard.button(text="⬅️ Volver", callback_data="admin_vip")
    keyboard.adjust(1, 2)  # 1 column for user buttons, 2 for pagination

    await safe_edit_message(
        callback_query,
        text,
        reply_markup=keyboard.as_markup()
    )


@admin_router.callback_query(F.data.startswith("vip_user_detail_"))
async def view_subscriber_detail(callback_query: CallbackQuery, session: AsyncSession, bot: Bot):
    """Display detailed information about a specific VIP subscriber."""
    # Extract user_id and page from callback data
    try:
        parts = callback_query.data.split("_")
        user_id = int(parts[3])
        # Get page if available (from the callback format "vip_user_detail_{user_id}_{page}")
        page = 1
        if len(parts) > 4:
            page = int(parts[4])
    except (ValueError, IndexError):
        await callback_query.answer("❌ ID de usuario inválido", show_alert=True)
        return

    # Get user subscription details using service method
    subscription = await SubscriptionService.get_active_vip_subscription(user_id, session)

    if not subscription:
        await callback_query.answer("❌ Usuario no encontrado o no tiene suscripción VIP activa", show_alert=True)
        return

    # Format the user details
    join_date = subscription.join_date.strftime("%d/%m/%Y %H:%M")
    expiry_date = subscription.expiry_date.strftime("%d/%m/%Y %H:%M")
    time_left = (subscription.expiry_date - datetime.now(timezone.utc)).days

    text = (
        f"**FICHA TÉCNICA DEL USUARIO**\n\n"
        f"👤 ID del Usuario: {subscription.user_id}\n"
        f"📅 Fecha de Registro: {join_date}\n"
        f"📅 Fecha de Expiración: {expiry_date}\n"
        f"⏳ Días Restantes: {time_left} días\n"
        f"💳 Token Usado: {subscription.token_id or 'N/A'}\n"
    )

    # Create keyboard with revoke and back buttons
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🚫 REVOCAR ACCESO", callback_data=f"vip_revoke_confirm_{user_id}_{page}")
    keyboard.button(text="⬅️ Volver a Lista", callback_data=f"vip_page_{page}")
    keyboard.adjust(1)

    await safe_edit_message(
        callback_query,
        text,
        reply_markup=keyboard.as_markup()
    )


@admin_router.callback_query(F.data.startswith("vip_revoke_confirm_"))
async def process_revocation(callback_query: CallbackQuery, session: AsyncSession, bot: Bot):
    """Process the revocation of VIP access for a specific user."""
    # Extract user_id and page from callback data
    try:
        parts = callback_query.data.split("_")
        user_id = int(parts[3])
        # Get page if available (from the callback format "vip_revoke_confirm_{user_id}_{page}")
        page = 1
        if len(parts) > 4:
            page = int(parts[4])
    except (ValueError, IndexError):
        await callback_query.answer("❌ ID de usuario inválido", show_alert=True)
        return

    # Call the service to revoke VIP access
    result = await SubscriptionService.revoke_vip_access(user_id, bot, session)

    if result["success"]:
        await callback_query.answer(f"✅ Usuario {user_id} expulsado y acceso revocado", show_alert=True)
        # Refresh back to the same page in the list
        await view_subscribers_list(callback_query, session, bot, page=page)
    else:
        await callback_query.answer(f"❌ Error: {result['error']}", show_alert=True)


# Callback handlers for main menu options
@admin_router.callback_query(F.data == "admin_config")
async def admin_config(callback_query: CallbackQuery, session: AsyncSession):
    """Show main configuration menu using MenuFactory with options to configure different aspects."""
    # Define configuration menu options according to the specification
    config_options = [
        ("💰 Gestionar Tarifas", "config_tiers"),  # Gestionar niveles de suscripción
        ("📡 Configurar Canales", "config_channels_menu"),  # Configurar canales
    ]

    menu_data = MenuFactory.create_menu(
        title="⚙️ Configuración Principal",
        options=config_options,
        back_callback="admin_main_menu",
        has_main=True
    )

    await safe_edit_message(
        callback_query,
        menu_data['text'],
        menu_data['markup']
    )


@admin_router.callback_query(F.data.in_({"vip_config", "free_config"}))
async def admin_channel_config(callback_query: CallbackQuery):
    """Muestra las opciones de configuración para un tipo de canal."""
    channel_type = "vip" if callback_query.data == "vip_config" else "free"

    if channel_type == "vip":
        title = "Configuración VIP"
        options = [
            ("📊 Ver Stats", "vip_stats"),
            ("💄 Configurar Reacciones", "vip_config_reactions"),
        ]
        back_callback = "admin_vip"
    else:  # free
        title = "Configuración Free"
        options = [
            ("📊 Ver Stats", "free_stats"),
            ("💄 Configurar Reacciones", "free_config_reactions"),
            ("⏱️ Configurar Tiempo de Espera", "free_wait_time_config"),
        ]
        back_callback = "admin_free"

    menu_data = MenuFactory.create_menu(
        title=title,
        options=options,
        back_callback=back_callback,
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
@admin_router.callback_query(F.data.in_({"vip_config_reactions", "free_config_reactions"}))
async def setup_reactions_start(callback_query: CallbackQuery, state: FSMContext):
    """Inicia el flujo de configuración de reacciones para un canal."""
    channel_type = "vip" if callback_query.data == "vip_config_reactions" else "free"
    await state.update_data(channel_type=channel_type)

    await state.set_state(ReactionSetupStates.waiting_reactions_input)

    channel_name_upper = channel_type.upper()
    instructions = (f"💋 Configuración de Reacciones Inline {channel_name_upper}\n"
                   f"Envía la lista de emojis permitidos separados por coma (ej: 👍, 🔥, 🚀). "
                   f"Se usarán como botones de interacción en las publicaciones.")

    await safe_edit_message(
        callback_query,
        instructions,
        reply_markup=None
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
    try:
        reactions_list = await ConfigService.setup_reactions(
            channel_type=channel_type,
            reactions_str=message.text,
            session=session
        )

        # Success: show list of reactions that were saved
        response_text = f"✅ Reacciones guardadas. Lista: {', '.join(reactions_list)}."
        await message.reply(response_text)

        # Clear the state
        await state.clear()

        # Rather than calling admin_vip or admin_free handlers that expect CallbackQuery,
        # we can create a simple menu to return to the appropriate configuration
        if channel_type == "vip":
            await message.reply("Regresando al menú de configuración VIP...")
            # We could send the appropriate menu here, but for now just return to general config
            # For a complete implementation, we would need to refactor to have shared functions
            # that generate the menu content
        else:  # free
            await message.reply("Regresando al menú de configuración Free...")

    except (ValueError, ConfigError) as e:
        # Error: show error message
        error = str(e)
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
        from bot.utils.ui import escape_markdownv2_text
        escaped_text = escape_markdownv2_text(response_text)
        await message.reply(escaped_text, parse_mode="MarkdownV2")
    else:
        from bot.utils.ui import escape_markdownv2_text
        escaped_text = escape_markdownv2_text(f"❌ Error al registrar el canal. Razón: {result['error']}. ¿El bot es administrador en ese canal?")
        await message.reply(escaped_text, parse_mode="MarkdownV2")

    # Clear the state
    await state.clear()


# Placeholder callback for coming soon features
@admin_router.callback_query(F.data == "feature_coming_soon")
async def feature_coming_soon(callback_query: CallbackQuery):
    """Generic callback for features that are coming soon."""
    await callback_query.answer("ℹ️ Próximamente: Esta funcionalidad está en desarrollo.", show_alert=True)


@admin_router.callback_query(F.data == "vip_generate_token")
async def vip_generate_token(callback_query: CallbackQuery, session: AsyncSession):
    """Generate VIP token with a simple flow"""
    # Get all tiers
    tiers = await ConfigService.get_all_tiers(session)

    if not tiers:
        await callback_query.answer("❌ No hay tarifas configuradas. Crea una tarifa primero.", show_alert=True)
        return

    # Create a simple menu to select a tier
    keyboard = InlineKeyboardBuilder()
    for tier in tiers:
        keyboard.button(text=f"{tier.name} (${tier.price_usd})", callback_data=f"token_generate_{tier.id}")

    keyboard.button(text="Volver", callback_data="admin_vip")
    keyboard.adjust(1)

    await safe_edit_message(
        callback_query,
        "Selecciona una tarifa para generar un token:",
        reply_markup=keyboard.as_markup()
    )


@admin_router.callback_query(F.data == "vip_config_tiers")
async def vip_config_tiers(callback_query: CallbackQuery, session: AsyncSession):
    """Configure VIP tiers - redirect to config tiers"""
    await callback_query.answer("Accediendo a la configuración de tarifas...", show_alert=False)
    # Call the existing handler
    await manage_tiers_menu(callback_query, session)


# Handler for inline reaction buttons
@admin_router.callback_query(ReactionCallback.filter())
async def process_inline_reaction(callback_query: CallbackQuery, callback_data: ReactionCallback, services: Services):
    """
    Handler for reaction buttons.
    Emits an event to the EventBus rather than processing the reaction directly.
    """
    # Respond immediately to remove the loading state in Telegram
    await callback_query.answer()

    # Extract reaction data from the callback_data
    # channel_type = callback_data.channel_type  # Unused variable
    emoji = callback_data.emoji

    # Define the event data
    event_data = {
        "user_id": callback_query.from_user.id,
        "channel_id": callback_query.message.chat.id,
        "emoji": emoji,
        "message_id": callback_query.message.message_id
    }

    # Emit the event to the EventBus (non-blocking)
    await services.bus.emit(Events.REACTION_ADDED, event_data)

    # Optional: Update reaction count in message if needed
    # For now, we just keep the original message


# Handler for content packs menu
@admin_router.callback_query(F.data == "admin_content_packs")
async def admin_content_packs_menu(callback_query: CallbackQuery, session: AsyncSession, services: Services):
    """
    Show content pack management menu with list of existing packs.
    """
    # Get all content packs
    packs = await services.gamification.get_all_content_packs(session)

    # Create menu
    keyboard = InlineKeyboardBuilder()

    # Add existing packs if any
    if packs:
        for pack in packs:
            keyboard.button(
                text=f"📦 {pack.name}",
                callback_data=f"pack_view_{pack.id}"
            )
    else:
        keyboard.button(text="❌ No hay packs disponibles", callback_data="noop")

    # Add "Create New Pack" button
    keyboard.button(text="➕ Crear Nuevo Pack", callback_data="pack_create_new")

    # Add "Volver" button
    keyboard.button(text="Volver", callback_data="admin_vip")

    keyboard.adjust(1)

    # Create message text
    if packs:
        text = f"📦 **Packs de Contenido Multimedia**\n\nTotal: {len(packs)} packs\n\nSelecciona un pack para verlo o crea uno nuevo."
    else:
        text = "📦 **Packs de Contenido Multimedia**\n\nNo hay packs de contenido creados aún.\n\nCrea un pack nuevo para empezar."

    await safe_edit_message(
        callback_query,
        text,
        reply_markup=keyboard.as_markup()
    )


# Handler for viewing pack details
@admin_router.callback_query(F.data.startswith("pack_view_"))
async def pack_view_detail(callback_query: CallbackQuery, session: AsyncSession, services: Services):
    """
    Show detailed view for a content pack.
    """
    # Extract pack ID
    pack_id = int(callback_query.data.split("_")[2])

    # Get the pack
    result = await session.execute(
        select(RewardContentPack).where(RewardContentPack.id == pack_id)
    )
    pack = result.scalar_one_or_none()

    if not pack:
        await callback_query.answer("❌ Pack no encontrado.", show_alert=True)
        return

    # Count files in the pack
    files_result = await session.execute(
        select(func.count(RewardContentFile.id)).where(RewardContentFile.pack_id == pack_id)
    )
    file_count = files_result.scalar()

    # Create message text with pack information
    text = (
        f"📦 **Pack de Contenido: {pack.name}**\n\n"
        f"📅 **Fecha de Creación**: {pack.created_at.strftime('%d/%m/%Y %H:%M')}\n"
        f"🖼️ **Archivos**: {file_count}\n\n"
        f"Utilice este pack asignándolo a un rango o como recompensa."
    )

    # Create keyboard with options
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Volver a Packs", callback_data="admin_content_packs")
    keyboard.adjust(1)

    await safe_edit_message(
        callback_query,
        text,
        reply_markup=keyboard.as_markup()
    )


# Handler to start content pack creation
@admin_router.callback_query(F.data == "pack_create_new")
async def start_pack_creation(callback_query: CallbackQuery, state: FSMContext):
    """
    Start the content pack creation flow.
    """
    # Store return context for nested creation (if any)
    # For now we just start the flow normally
    await state.set_state(ContentPackCreationStates.waiting_pack_name)

    # Ask for pack name
    await callback_query.message.edit_text(
        escape_markdownv2_text("📦 **Creación de Pack de Contenido**\n\nPonle un nombre único a este Pack de Contenido:"),
        parse_mode="MarkdownV2"
    )

    # Answer the callback
    await callback_query.answer()


# Handler to process pack name
@admin_router.message(ContentPackCreationStates.waiting_pack_name)
async def process_pack_name(message: Message, state: FSMContext, session: AsyncSession, services: Services):
    """
    Process the pack name and move to media upload state.
    """
    # Get the pack name
    pack_name = message.text.strip()

    if not pack_name:
        await message.reply("❌ El nombre del pack no puede estar vacío. Introduce un nombre válido:")
        return

    # Try to create the pack
    pack = await services.gamification.create_content_pack(pack_name, session)

    if pack is None:
        await message.reply(f"❌ Ya existe un pack con el nombre '{pack_name}'. Elige otro nombre:")
        return

    # Store the pack ID in the state
    await state.update_data(current_pack_id=pack.id)
    await state.set_state(ContentPackCreationStates.waiting_media_files)

    # Inform the user
    await message.reply(
        f"✅ Pack '{pack_name}' creado exitosamente.\n\n"
        f"Ahora envía las fotos, videos o documentos una por una.\n"
        f"Cuando termines, haz clic en el botón '🏁 Finalizar'."
    )

    # Add inline keyboard with finish button
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🏁 Finalizar", callback_data="pack_finish_creation")
    await message.answer("Selecciona cuando hayas terminado de subir archivos:", reply_markup=keyboard.as_markup())


# Handler to finish pack creation
@admin_router.callback_query(F.data == "pack_finish_creation")
async def finish_pack_creation(callback_query: CallbackQuery, state: FSMContext, session: AsyncSession, services: Services):
    """
    Finish the pack creation and redirect based on return context.
    """
    # Get state data
    data = await state.get_data()

    # Clear the state
    await state.clear()

    # Get return context if any
    return_context = data.get("return_context")

    # Inform the user
    await safe_callback_answer(callback_query, "✅ Pack creado y guardado exitosamente", show_alert=True)

    # Check if we have a return context
    if return_context:
        # Check if this is a nested creation from rank management
        action = return_context.get('action')
        if action == 'return_to_rank_after_pack_creation':
            rank_id = return_context.get('rank_id')
            if rank_id:
                # Update callback data to the rank edit format and call the handler
                callback_query.data = f"rank_edit_{rank_id}"
                await rank_edit_detail(callback_query, session, services)
                return
        # For any other return context, go back to the origin
        await admin_content_packs_menu(callback_query, session, services)
    else:
        # Default: return to content packs menu
        await admin_content_packs_menu(callback_query, session, services)




# Handler to process media files
@admin_router.message(ContentPackCreationStates.waiting_media_files)
async def process_media_file(message: Message, state: FSMContext, session: AsyncSession, services: Services):
    """
    Process media files and add them to the current pack.
    """
    # Determine the media type and extract file info
    file_id = None
    file_unique_id = None
    media_type = None

    # Check for different types of media
    if message.photo:
        # Use the largest photo (last in the list)
        photo = message.photo[-1]  # Get the highest resolution
        file_id = photo.file_id
        file_unique_id = photo.file_unique_id
        media_type = 'photo'
    elif message.video:
        file_id = message.video.file_id
        file_unique_id = message.video.file_unique_id
        media_type = 'video'
    elif message.document:
        file_id = message.document.file_id
        file_unique_id = message.document.file_unique_id
        media_type = 'document'
    else:
        await message.reply("❌ Formato no soportado. Envía una foto, video o documento.")
        return

    # Get the current pack ID from state
    data = await state.get_data()
    pack_id = data.get("current_pack_id")

    if not pack_id:
        await message.reply("❌ Error: No hay un pack activo. Comienza la creación de pack primero.")
        return

    # Add the file to the pack
    success = await services.gamification.add_file_to_pack(
        pack_id=pack_id,
        file_id=file_id,
        unique_id=file_unique_id,
        media_type=media_type,
        session=session
    )

    if success:
        # Count how many files are now in the pack
        result = await session.execute(
            select(RewardContentFile).where(RewardContentFile.pack_id == pack_id)
        )
        files = result.scalars().all()

        await message.reply(f"➕ Archivo guardado ({len(files)} archivos en total). Continúa enviando archivos o finaliza.")
    else:
        await message.reply("❌ Error al guardar el archivo. Inténtalo de nuevo.")


# Handler for rank management menu
@admin_router.callback_query(F.data == "vip_manage_ranks")
async def vip_manage_ranks_menu(callback_query: CallbackQuery, session: AsyncSession, services: Services):
    """
    Show rank management menu with list of all ranks.
    """
    # Get all ranks
    ranks = await services.gamification.get_all_ranks(session)

    # Create menu
    keyboard = InlineKeyboardBuilder()

    # Add existing ranks if any
    if ranks:
        for rank in ranks:
            keyboard.button(
                text=f"🏆 {rank.name} ({rank.min_points} pts)",
                callback_data=f"rank_edit_{rank.id}"
            )
    else:
        keyboard.button(text="❌ No hay rangos disponibles", callback_data="noop")

    # Add "Volver" button
    keyboard.button(text="Volver", callback_data="admin_vip")

    keyboard.adjust(1)

    # Create message text
    if ranks:
        text = f"🏆 **Gestión de Rangos**\n\nTotal: {len(ranks)} rangos\n\nSelecciona un rango para configurar sus recompensas."
    else:
        text = "🏆 **Gestión de Rangos**\n\nNo hay rangos configurados en el sistema.\n\nLos rangos se crean automáticamente al inicializar la base de datos."

    await safe_edit_message(
        callback_query,
        text,
        reply_markup=keyboard.as_markup()
    )


# Handler to edit a specific rank
@admin_router.callback_query(F.data.startswith("rank_edit_"))
async def rank_edit_detail(callback_query: CallbackQuery, session: AsyncSession, services: Services):
    """
    Show detailed view for editing a specific rank.
    """
    # Extract rank ID
    rank_id = int(callback_query.data.split("_")[2])

    # Get the rank
    rank = await services.gamification.get_rank_by_id(rank_id, session)

    if not rank:
        await callback_query.answer("❌ Rango no encontrado.", show_alert=True)
        return

    # Get the associated pack if any
    pack_name = "Ninguno"
    if rank.reward_content_pack_id:
        # We need to get pack information as well
        pack_result = await session.execute(
            select(RewardContentPack).where(RewardContentPack.id == rank.reward_content_pack_id)
        )
        pack = pack_result.scalar_one_or_none()
        if pack:
            pack_name = pack.name

    # Create message text with current configuration
    text = (
        f"🏆 **Rango: {rank.name}**\n\n"
        f"⭐️ **Puntos**: {rank.min_points}\n"
        f"🎁 **Premio VIP**: {rank.reward_vip_days} días\n"
        f"📦 **Pack**: {pack_name}"
    )

    # Create keyboard with edit options
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✏️ Editar Días VIP", callback_data=f"rank_set_vip_{rank.id}")
    keyboard.button(text="📦 Asignar Pack", callback_data=f"rank_set_pack_{rank.id}")
    keyboard.button(text="⬅️ Volver", callback_data="vip_manage_ranks")

    keyboard.adjust(1)

    await safe_edit_message(
        callback_query,
        text,
        reply_markup=keyboard.as_markup()
    )


# Helper function to display rank details (to avoid mock objects)
async def display_rank_detail(chat_id: int, rank_id: int, session: AsyncSession, services: Services, bot):
    """
    Helper function to display rank details in different contexts (used to avoid mock objects).
    """
    # Get the rank
    rank = await services.gamification.get_rank_by_id(rank_id, session)

    if not rank:
        # Send error message since we can't use callback_query.answer
        await bot.send_message(chat_id, "❌ Rango no encontrado.")
        return

    # Get the associated pack if any
    pack_name = "Ninguno"
    if rank.reward_content_pack_id:
        # We need to get pack information as well
        pack_result = await session.execute(
            select(RewardContentPack).where(RewardContentPack.id == rank.reward_content_pack_id)
        )
        pack = pack_result.scalar_one_or_none()
        if pack:
            pack_name = pack.name

    # Create message text with current configuration
    text = (
        f"🏆 **Rango: {rank.name}**\n\n"
        f"⭐️ **Puntos**: {rank.min_points}\n"
        f"🎁 **Premio VIP**: {rank.reward_vip_days} días\n"
        f"📦 **Pack**: {pack_name}"
    )

    # Create keyboard with edit options
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✏️ Editar Días VIP", callback_data=f"rank_set_vip_{rank.id}")
    keyboard.button(text="📦 Asignar Pack", callback_data=f"rank_set_pack_{rank.id}")
    keyboard.button(text="⬅️ Volver", callback_data="vip_manage_ranks")

    keyboard.adjust(1)

    # Send message with rank details
    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=None,  # This won't work with edit_message_text, we need a different approach
        text=text,
        reply_markup=keyboard.as_markup()
    )


async def show_rank_detail_message(chat_id: int, rank_id: int, session: AsyncSession, services: Services, bot):
    """
    Helper function to send rank details as a new message (alternative approach).
    """
    # Get the rank
    rank = await services.gamification.get_rank_by_id(rank_id, session)

    if not rank:
        # Send error message since we can't use callback_query.answer
        await bot.send_message(chat_id, "❌ Rango no encontrado.")
        return

    # Get the associated pack if any
    pack_name = "Ninguno"
    if rank.reward_content_pack_id:
        # We need to get pack information as well
        pack_result = await session.execute(
            select(RewardContentPack).where(RewardContentPack.id == rank.reward_content_pack_id)
        )
        pack = pack_result.scalar_one_or_none()
        if pack:
            pack_name = pack.name

    # Create message text with current configuration
    text = (
        f"🏆 **Rango: {rank.name}**\n\n"
        f"⭐️ **Puntos**: {rank.min_points}\n"
        f"🎁 **Premio VIP**: {rank.reward_vip_days} días\n"
        f"📦 **Pack**: {pack_name}"
    )

    # Create keyboard with edit options
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✏️ Editar Días VIP", callback_data=f"rank_set_vip_{rank.id}")
    keyboard.button(text="📦 Asignar Pack", callback_data=f"rank_set_pack_{rank.id}")
    keyboard.button(text="⬅️ Volver", callback_data="vip_manage_ranks")

    keyboard.adjust(1)

    # Send message with rank details
    await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=keyboard.as_markup()
    )


# Handler to set VIP days for a rank
@admin_router.callback_query(F.data.startswith("rank_set_vip_"))
async def rank_set_vip_days_start(callback_query: CallbackQuery, state: FSMContext):
    """
    Start FSM flow to set VIP days for a rank.
    """
    # Extract rank ID
    rank_id = int(callback_query.data.split("_")[3])

    # Store rank ID in state for later use
    await state.update_data(current_rank_id=rank_id)
    await state.set_state(RankConfigStates.waiting_vip_days)

    # Ask for VIP days
    await callback_query.message.edit_text(
        "🔢 **Editar Días VIP**\n\n"
        "Introduce el número de días de suscripción VIP que se otorgan al alcanzar este rango (0 para ninguno):"
    )

    # Answer the callback
    await callback_query.answer()


# Handler to process VIP days input
@admin_router.message(RankConfigStates.waiting_vip_days)
async def process_vip_days_input(message: Message, state: FSMContext, session: AsyncSession, services: Services):
    """
    Process the VIP days input and update the rank.
    """
    try:
        # Get the rank ID from state
        data = await state.get_data()
        rank_id = data.get("current_rank_id")

        if not rank_id:
            await message.reply("❌ Error: No se encontró el rango. Intenta de nuevo.")
            await state.clear()
            return

        # Parse the input
        vip_days_str = message.text.strip()
        vip_days = int(vip_days_str)

        if vip_days < 0:
            await message.reply("❌ Los días VIP deben ser un número positivo o cero. Inténtalo de nuevo:")
            return

        # Update the rank with new VIP days
        updated_rank = await services.gamification.update_rank_rewards(
            rank_id=rank_id,
            session=session,
            vip_days=vip_days
        )

        if not updated_rank:
            await message.reply("❌ Error al actualizar el rango. Intenta de nuevo.")
            await state.clear()
            return

        # Clear state
        await state.clear()

        # Confirm and show updated rank
        await message.reply(f"✅ Días VIP actualizados a {vip_days}.")

        # Show updated rank details by sending a new message with the details
        await show_rank_detail_message(message.chat.id, rank_id, session, services, message.bot)

    except ValueError:
        await message.reply("❌ Por favor, introduce un número válido. Inténtalo de nuevo:")
    except Exception as e:
        await message.reply(f"❌ Error inesperado: {str(e)}. Intenta de nuevo.")
        await state.clear()


# Handler to start pack assignment flow
@admin_router.callback_query(F.data.startswith("rank_set_pack_"))
async def rank_set_pack_start(callback_query: CallbackQuery, session: AsyncSession, services: Services):
    """
    Show available packs and option to create a new one for assignment to this rank.
    """
    # Extract rank ID
    rank_id = int(callback_query.data.split("_")[3])

    # Get all content packs
    packs = await services.gamification.get_all_content_packs(session)

    # Create menu
    keyboard = InlineKeyboardBuilder()

    # Add existing packs if any
    if packs:
        for pack in packs:
            keyboard.button(
                text=f"📦 {pack.name}",
                callback_data=f"rank_bind_pack_{rank_id}_{pack.id}"
            )
    else:
        keyboard.button(text="❌ No hay packs disponibles", callback_data="noop")

    # Add "Create New" button with nested creation context
    keyboard.button(text="➕ Crear Nuevo", callback_data=f"rank_create_pack_nested_{rank_id}")

    # Add "Volver" button
    keyboard.button(text="Volver", callback_data=f"rank_edit_{rank_id}")

    keyboard.adjust(1)

    # Create message text
    if packs:
        text = f"📦 **Asignar Pack de Contenido al Rango**\n\nSelecciona un pack existente o crea uno nuevo:"
    else:
        text = "📦 **Asignar Pack de Contenido al Rango**\n\nNo hay packs de contenido disponibles.\n\nCrea un pack nuevo para asignarlo al rango."

    await safe_edit_message(
        callback_query,
        text,
        reply_markup=keyboard.as_markup()
    )


# Handler to bind a pack to a rank
@admin_router.callback_query(F.data.startswith("rank_bind_pack_"))
async def rank_bind_pack(callback_query: CallbackQuery, session: AsyncSession, services: Services):
    """
    Bind a selected pack to the rank.
    """
    # Extract rank_id and pack_id from callback data
    parts = callback_query.data.split("_")
    rank_id = int(parts[3])
    pack_id = int(parts[4])

    # Update the rank with the selected pack
    updated_rank = await services.gamification.update_rank_rewards(
        rank_id=rank_id,
        session=session,
        pack_id=pack_id
    )

    if not updated_rank:
        await callback_query.answer("❌ Error al asignar el pack al rango.", show_alert=True)
        return

    # Get the pack name for confirmation
    pack_result = await session.execute(
        select(RewardContentPack).where(RewardContentPack.id == pack_id)
    )
    pack = pack_result.scalar_one_or_none()
    pack_name = pack.name if pack else "Pack"

    # Confirm and return to rank edit
    await callback_query.answer(f"✅ Pack '{pack_name}' asignado al rango.", show_alert=True)

    # Show updated rank details by sending a new message with the details
    await show_rank_detail_message(callback_query.message.chat.id, rank_id, session, services, callback_query.message.bot)


# Handler for nested pack creation
@admin_router.callback_query(F.data.startswith("rank_create_pack_nested_"))
async def rank_create_pack_nested(callback_query: CallbackQuery, state: FSMContext):
    """
    Start nested pack creation flow with return context set to assign the new pack to the rank.
    """
    # Extract rank ID
    rank_id = int(callback_query.data.split("_")[4])

    # Define return context
    return_context = {
        'action': 'return_to_rank_after_pack_creation',
        'rank_id': rank_id
    }

    # Save the return context in the state
    await state.update_data(return_context=return_context)

    # Redirect to the pack creation flow from P27.0
    await start_pack_creation(callback_query, state)
