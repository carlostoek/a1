from aiogram import Bot
from typing import Callable, Any, Annotated

# Importar todos los servicios existentes:
from bot.services.config_service import ConfigService
from bot.services.subscription_service import SubscriptionService
from bot.services.stats_service import StatsService
from bot.services.channel_service import ChannelManagementService
from bot.services.notification_service import NotificationService


class ServiceContainer:
    """Contenedor de Inyección de Dependencias para todos los servicios del bot."""

    def __init__(self, bot: Bot):
        # 1. Instancia Base
        self.bot = bot

        # 2. Inicialización de Servicios Core (Singletons)
        # Nota: Los servicios deben ser ligeros y no deben abrir/cerrar recursos como DB Sessions
        # La DB Session será inyectada en el método de cada servicio.

        self._config_service = ConfigService()
        self._notification_service = NotificationService(bot=self.bot)
        self._subscription_service = SubscriptionService()
        self._stats_service = StatsService()
        self._channel_service = ChannelManagementService()
        # Inicializar otros servicios aquí...

    # --- Propiedades de Acceso Rápido ---

    @property
    def config(self) -> ConfigService:
        """Acceso al servicio de Configuración (BotConfig)."""
        return self._config_service

    @property
    def notify(self) -> NotificationService:
        """Acceso al servicio de Notificaciones (Mensajería al usuario)."""
        return self._notification_service

    @property
    def subs(self) -> SubscriptionService:
        """Acceso al servicio de Suscripciones (Usuarios VIP)."""
        return self._subscription_service
        
    @property
    def stats(self) -> StatsService:
        """Acceso al servicio de Estadísticas (Reportes)."""
        return self._stats_service
        
    @property
    def channel_manager(self) -> ChannelManagementService:
        """Acceso al servicio de Gestión de Canales (Posteo, IDs)."""
        return self._channel_service


# --- Definición del Resolver de Dependencias de Aiogram 3 ---

def get_services_container(handler_data: dict) -> ServiceContainer:
    """Función resolvedora que extrae el ServiceContainer del contexto del manejador."""
    # El objeto se almacena en el Dispatcher context y se propaga
    return handler_data['services']


# Tipo anotado para usar en la firma de los handlers
Services = Annotated[ServiceContainer, get_services_container]