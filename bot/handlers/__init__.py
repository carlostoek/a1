"""
Paquete de manejadores para el Bot de Telegram.
Contiene todos los manejadores de mensajes y callbacks para el bot.
"""

from .wizard_handler import router as wizard_router

__all__ = [
    "wizard_router"
]
