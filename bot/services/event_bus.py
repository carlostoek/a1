import asyncio
from bot.utils.sexy_logger import get_logger
from enum import Enum
from typing import Callable, Dict, List, Any, Awaitable

# Definición de tipos para los Listeners (funciones asíncronas)
EventHandler = Callable[[str, Dict[str, Any]], Awaitable[None]]

class EventBus:
    """
    Bus de eventos asíncrono simple para desacoplar módulos.
    """
    def __init__(self):
        # Diccionario: Clave=NombreEvento, Valor=Lista de funciones que escuchan
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self.logger = get_logger(__name__)

    def subscribe(self, event_name: str, handler: EventHandler):
        """Registra una función para escuchar un evento específico."""
        self._subscribers.setdefault(event_name, []).append(handler)
        self.logger.event(f"Listener registrado para evento: {event_name}")

    async def emit(self, event_name: str, data: Dict[str, Any]):
        """
        Publica un evento. Ejecuta todos los listeners suscritos de forma concurrente
        sin bloquear el flujo principal (fire-and-forget).
        """
        listeners = self._subscribers.get(event_name, [])

        # Ejecutar todos los listeners concurrentemente
        # Usamos asyncio.create_task para que si un listener falla o tarda,
        # no detenga al emisor original.
        for handler in listeners:
            asyncio.create_task(self._run_handler(handler, event_name, data))

    async def _run_handler(self, handler: EventHandler, event_name: str, data: Dict[str, Any]):
        """Wrapper seguro para ejecutar handlers y capturar errores."""
        try:
            await handler(event_name, data)
        except Exception as e:
            self.logger.event(f"Error en EventBus manejando '{event_name}': {e}", exc_info=True)

# Lista de constantes de eventos conocidos (Para evitar magic strings)
class Events(str, Enum):
    REACTION_ADDED = "reaction_added"      # Alguien reaccionó
    SUBSCRIPTION_NEW = "subscription_new"  # Alguien compró VIP
    VIP_EXPIRED = "vip_expired"            # Alguien perdió VIP
    LEVEL_UP = "level_up"                  # (Futuro) Subió de nivel
