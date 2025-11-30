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
                    has_back: bool = True, 
                    has_main: bool = True) -> Dict[str, Any]:
        """
        Genera un menú estandarizado.

        Args:
            title: Título del menú.
            options: Lista de tuplas (Texto del botón, Callback data).
            has_back: Incluir botón 'Volver' (callback 'admin_back').
            has_main: Incluir botón 'Menú Principal' (callback 'admin_main_menu').

        Returns:
            dict: {'text': str, 'markup': InlineKeyboardMarkup}
        """
        # Lógica de construcción
        keyboard = []
        
        # 1. Botones de opciones
        # Agrupar las opciones en filas lógicas (ej: 2 por fila, si son más de 4)
        for i in range(0, len(options), 2):
            row = []
            for text, data in options[i:i+2]:
                row.append(cls._create_button(text, data))
            if row:  # Only add non-empty rows
                keyboard.append(row)

        # 2. Botones de Navegación Estandar
        nav_row = []
        if has_back:
            nav_row.append(cls._create_button("⬅️ Volver", "admin_back"))
        if has_main:
            nav_row.append(cls._create_button("🏠 Principal", "admin_main_menu"))
        
        if nav_row:
            keyboard.append(nav_row)

        # Retorno estandarizado
        return {
            'text': f"**{title.upper()}**\n\nSelecciona una opción:",
            'markup': InlineKeyboardMarkup(inline_keyboard=keyboard)
        }

    @classmethod
    def create_simple_menu(cls,
                          title: str,
                          options: List[Tuple[str, str]]) -> Dict[str, Any]:
        """
        Creates a simple menu without navigation buttons.
        
        Args:
            title: Title of the menu
            options: List of tuples (Button text, Callback data)
            
        Returns:
            dict: {'text': str, 'markup': InlineKeyboardMarkup}
        """
        return cls.create_menu(title, options, has_back=False, has_main=False)