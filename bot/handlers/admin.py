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
from aiogram.exceptions import TelegramBadRequest
from bot.middlewares.auth import AdminAuthMiddleware
from bot.middlewares.db import DBSessionMiddleware
from bot.services.subscription_service import SubscriptionService
from bot.services.channel_service import ChannelManagementService
from bot.services.config_service import ConfigService
from bot.services.stats_service import StatsService
from bot.services.exceptions import ServiceError, SubscriptionError
from bot.states import SubscriptionTierStates, ChannelSetupStates, PostSendingStates, ReactionSetupStates, WaitTimeSetupStates
from bot.config import Settings
from datetime import datetime, timedelta, timezone
from bot.utils.ui import MenuFactory

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
        ("📢 Enviar Publicación", "admin_send_channel_post"),
        ("👥 Gestionar Suscriptores", "vip_manage"),
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
        ("📢 Enviar Publicación", "send_to_free_channel"),
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
async def admin_stats_menu(callback_query: CallbackQuery, session: AsyncSession):
    """Show main statistics menu with three options: General, VIP, Free."""
    # Create the main stats menu with three options
    stats_options = [
        ("📊 General", "stats_general"),
        ("💎 VIP", "stats_vip"),
        ("💬 FREE", "stats_free"),
    ]

    menu_data = MenuFactory.create_menu(
        title="📊 Estadísticas",
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
    except Exception as e:
        await callback_query.answer(f"Error al obtener estadísticas generales: {str(e)}", show_alert=True)


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
    except Exception as e:
        await callback_query.answer(f"Error al obtener estadísticas VIP: {str(e)}", show_alert=True)


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
    except Exception as e:
        await callback_query.answer(f"Error al obtener estadísticas FREE: {str(e)}", show_alert=True)


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
        await message.reply(response_text)

        # Acknowledge completion after success
        await message.reply("Regresando al menú principal para continuar.")
    else:
        # Error: show specific error message from service
        error = result["error"]
        response_text = f"❌ {error}"
        await message.reply(response_text)

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

        await message.reply(
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

    await bot.send_message(
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
    """Show general configuration status dashboard using ConfigService."""
    # Get configuration status
    config_status = await ConfigService.get_config_status(session)

    # Format the configuration status report
    vip_channel_status = "✅" if config_status["vip_channel_id"] else "❌"
    free_channel_status = "✅" if config_status["free_channel_id"] else "❌"
    tier_status = "✅" if config_status["active_tiers_count"] > 0 else "❌"
    vip_reactions_status = "✅" if config_status["vip_reactions"] else "❌"
    free_reactions_status = "✅" if config_status["free_reactions"] else "❌"

    # Format reaction emojis for display
    vip_reactions_display = ", ".join(config_status["vip_reactions"]) if config_status["vip_reactions"] else "Pendiente"
    free_reactions_display = ", ".join(config_status["free_reactions"]) if config_status["free_reactions"] else "Pendiente"

    # Build the report text
    report_text = (
        "⚙️ **ESTADO GENERAL DEL BOT**\n\n"
        "**CANALES:**\n"
        f"- Canal VIP: {vip_channel_status} (ID: {config_status['vip_channel_id'] or 'Pendiente'})\n"
        f"- Canal FREE: {free_channel_status} (ID: {config_status['free_channel_id'] or 'Pendiente'})\n\n"
        "**NEGOCIO:**\n"
        f"- Tarifas Activas: {tier_status} {config_status['active_tiers_count']} Tarifa(s)\n"
        f"- Tiempo de Espera FREE: {config_status['wait_time_minutes']} minutos\n\n"
        "**REACCIONES:**\n"
        f"- Reacciones VIP: {vip_reactions_status} ({vip_reactions_display})\n"
        f"- Reacciones FREE: {free_reactions_status} ({free_reactions_display})"
    )

    # Create keyboard with back button only
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="⬅️ Volver", callback_data="admin_main_menu")

    await safe_edit_message(
        callback_query,
        report_text,
        reply_markup=keyboard.as_markup()
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
        await message.reply(response_text)
    else:
        await message.reply(f"❌ Error al registrar el canal. Razón: {result['error']}. ¿El bot es administrador en ese canal?")

    # Clear the state
    await state.clear()
