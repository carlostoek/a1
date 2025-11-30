"""
UI utilities for the Telegram Admin Bot.
Contains standardized components for creating menus and UI elements.
"""
from typing import List, Tuple, Dict, Any, Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


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
        menu_text = f"**{title.upper()}**\n\nSelecciona una opción:"
        if description:
            menu_text = f"{description}\n\n{menu_text}"

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
            # CRÍTICO: Formato de Callback Data
            callback_data = f"react_{channel_type}_{emoji}"
            button = cls._create_button(emoji, callback_data)
            row.append(button)

        # Return markup with buttons in a single row
        return InlineKeyboardMarkup(inline_keyboard=[row])