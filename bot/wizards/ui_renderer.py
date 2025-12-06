from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


class WizardUIRenderer:
    @staticmethod
    def yes_no_keyboard():
        """Creates a simple yes/no keyboard for wizard steps."""
        keyboard = [
            [
                InlineKeyboardButton(text="✅ Sí", callback_data="yes"),
                InlineKeyboardButton(text="❌ No", callback_data="no"),
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)