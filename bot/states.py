"""
FSM States definitions for the Telegram Admin Bot.
"""
from aiogram.fsm.state import State, StatesGroup


class ChannelSetupStates(StatesGroup):
    # Usado para esperar el ID o el mensaje reenviado del canal (VIP o Free)
    waiting_channel_id_or_forward = State()


class PostSendingStates(StatesGroup):
    waiting_post_content = State()          # Espera el mensaje (texto/foto/video)
    waiting_reaction_decision = State()     # (NUEVO) Espera Sí/No para adjuntar reacciones
    waiting_confirmation = State()          # Espera confirmación final tras preview


class SubscriptionTierStates(StatesGroup):
    waiting_tier_name = State()
    waiting_tier_duration = State() # Duración en DÍAS
    waiting_tier_price = State()    # Precio Float
    waiting_tier_selection = State() # Para edición/eliminación


class FreeConfigStates(StatesGroup):
    waiting_wait_time_minutes = State()


class WaitTimeSetupStates(StatesGroup):
    waiting_wait_time_minutes = State()  # Espera el valor entero del tiempo de espera en minutos


class ReactionSetupStates(StatesGroup):
    waiting_reactions_input = State()  # Espera la cadena de emojis separados por coma.


class ContentPackCreationStates(StatesGroup):
    waiting_pack_name = State()
    waiting_media_files = State()  # Loop para subir múltiples archivos