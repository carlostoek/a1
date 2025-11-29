"""
FSM States definitions for the Telegram Admin Bot.
"""
from aiogram.fsm.state import State, StatesGroup


class FreeChannelSetupStates(StatesGroup):
    waiting_channel_link = State()
    waiting_channel_id = State()
    waiting_wait_time = State()


class VIPChannelSetupStates(StatesGroup):
    waiting_channel_link = State()
    waiting_channel_id = State()


class PostSendingStates(StatesGroup):
    waiting_post_content = State()
    waiting_confirmation = State()


class SubscriptionTierStates(StatesGroup):
    waiting_tier_name = State()
    waiting_tier_duration = State() # Duración en DÍAS
    waiting_tier_price = State()    # Precio Float
    waiting_tier_selection = State() # Para edición/eliminación