"""
UI utilities for the Telegram Admin Bot.
Contains standardized components for creating menus and UI elements.
"""
from typing import List, Tuple, Dict, Any, Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters.callback_data import CallbackData
import re


class ReactionCallback(CallbackData, prefix="react"):
    """Callback data for reaction buttons"""
    channel_type: str
    emoji: str

def escape_markdownv2_text(text: str) -> str:
    """
    Escapes special characters in text for MarkdownV2 formatting.

    Args:
        text: The text to escape

    Returns:
        Escaped text safe for MarkdownV2
    """
    # List of special characters that need escaping in MarkdownV2
    special_chars = r'([_*\[\]()~`>#+\-=|{}.!\\])'
    # Replace each special character with its escaped version
    escaped_text = re.sub(special_chars, r'\\\1', text)
    return escaped_text


class MenuFactory:
    """
    Fábrica estandarizada para crear teclados inline de administración.
    Garantiza la consistencia en la navegación (Back/Main).
    """

    @staticmethod
    def _create_button(text: str, callback_data: str) -> InlineKeyboardButton:
        """Helper interno"""
        return InlineKeyboardButton(text=text, callback_data=callback_data)

    @classmethod
    def create_menu(cls,
                    title: str,
                    options: List[Tuple[str, str]],
                    description: Optional[str] = None,
                    back_callback: Optional[str] = None,
                    has_main: bool = True) -> Dict[str, Any]:
        """
        Genera un menú estandarizado.

        Args:
            title: Título del menú.
            options: Lista de tuplas (Texto del botón, Callback data).
            description: Texto opcional para mostrar sobre el título del menú.
            back_callback: Callback data para el botón 'Volver'. Si es None, no se muestra.
            has_main: Incluir botón 'Menú Principal' (callback 'admin_main_menu').

        Returns:
            dict: {'text': str, 'markup': InlineKeyboardMarkup}
        """
        # Lógica de construcción
        keyboard = []

        # 1. Botones de opciones
        # Agrupar las opciones en filas lógicas (ej: 2 por fila)
        for i in range(0, len(options), 2):
            row = []
            for text, data in options[i:i+2]:
                row.append(cls._create_button(text, data))
            if row:  # Only add non-empty rows
                keyboard.append(row)

        # 2. Botones de Navegación Estandar
        nav_row = []
        if back_callback:
            nav_row.append(cls._create_button("⬅️ Volver", back_callback))
        if has_main:
            nav_row.append(cls._create_button("🏠 Principal", "admin_main_menu"))

        if nav_row:
            keyboard.append(nav_row)

        # Retorno estandarizado
        escaped_title = escape_markdownv2_text(title.upper())
        menu_text = f"**{escaped_title}**\n\nSelecciona una opción:"
        if description:
            escaped_description = escape_markdownv2_text(description)
            menu_text = f"{escaped_description}\n\n{menu_text}"

        return {
            'text': menu_text,
            'markup': InlineKeyboardMarkup(inline_keyboard=keyboard)
        }

    @classmethod
    def create_simple_menu(cls,
                          title: str,
                          options: List[Tuple[str, str]]) -> Dict[str, Any]:
        """
        Crea un menú simple sin botones de navegación.

        Args:
            title: Título del menú.
            options: Lista de tuplas (Texto del botón, Callback data).

        Returns:
            dict: {'text': str, 'markup': InlineKeyboardMarkup}
        """
        return cls.create_menu(title, options, has_main=False)

    @classmethod
    def create_reaction_keyboard(cls, channel_type: str, reactions_list: List[str]) -> InlineKeyboardMarkup:
        """
        Create an inline keyboard with reaction buttons for posts.

        Args:
            channel_type: 'vip' or 'free' channel type
            reactions_list: List of emojis to use as reaction buttons

        Returns:
            InlineKeyboardMarkup with reaction buttons
        """
        # Create buttons in a single row for reactions
        row = []
        for emoji in reactions_list:
            # Use ReactionCallback instead of manual string formatting
            callback_obj = ReactionCallback(channel_type=channel_type, emoji=emoji)
            button = cls._create_button(emoji, callback_obj.pack())
            row.append(button)

        # Return markup with buttons in a single row
        return InlineKeyboardMarkup(inline_keyboard=[row])

    @classmethod
    def create_pagination_keyboard(cls, current_page: int, total_pages: int, callback_prefix: str) -> List[InlineKeyboardButton]:
        """
        Create a pagination keyboard with navigation controls.

        Args:
            current_page: Current page number (1-indexed)
            total_pages: Total number of pages
            callback_prefix: Prefix for callback data (e.g., 'vip_page')

        Returns:
            List of InlineKeyboardButton for pagination controls
        """
        buttons = []

        # Previous page button
        if current_page > 1:
            prev_button = cls._create_button("⬅️", f"{callback_prefix}_{current_page - 1}")
            buttons.append(prev_button)

        # Current page / total pages indicator
        page_info_button = cls._create_button(f"{current_page}/{total_pages}", "noop")  # noop callback for info display
        buttons.append(page_info_button)

        # Next page button
        if current_page < total_pages:
            next_button = cls._create_button("➡️", f"{callback_prefix}_{current_page + 1}")
            buttons.append(next_button)

        return buttons