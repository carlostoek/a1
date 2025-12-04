"""
Sistema de logging colorido y atractivo con emojis para mejor visualización en consola.
Sexy Logger - Un logger que hace que tus logs se vean increíbles.
"""
import logging
import sys
from datetime import datetime
from typing import Optional


class Colors:
    """Códigos ANSI para colores en la terminal."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    # Colores básicos
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'

    # Colores brillantes
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'

    # Fondos
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'


class LogStyle:
    """Estilos predefinidos para diferentes tipos de logs."""

    def __init__(self, emoji: str, color: str, name: str):
        self.emoji = emoji
        self.color = color
        self.name = name

    def format_prefix(self) -> str:
        """Retorna el prefijo formateado con emoji y color."""
        return f"{self.color}{self.emoji} {self.name}{Colors.RESET}"


# Estilos predefinidos para cada nivel de log
STYLES = {
    'DEBUG': LogStyle('🔍', Colors.CYAN, 'DEBUG'),
    'INFO': LogStyle('ℹ️ ', Colors.BRIGHT_BLUE, 'INFO'),
    'WARNING': LogStyle('⚠️ ', Colors.YELLOW, 'WARNING'),
    'ERROR': LogStyle('❌', Colors.RED, 'ERROR'),
    'CRITICAL': LogStyle('💥', Colors.BG_RED + Colors.WHITE, 'CRITICAL'),

    # Estilos personalizados
    'STARTUP': LogStyle('🚀', Colors.BRIGHT_GREEN, 'STARTUP'),
    'SHUTDOWN': LogStyle('🛑', Colors.BRIGHT_RED, 'SHUTDOWN'),
    'SUCCESS': LogStyle('✅', Colors.BRIGHT_GREEN, 'SUCCESS'),
    'DATABASE': LogStyle('🗄️ ', Colors.MAGENTA, 'DATABASE'),
    'API': LogStyle('🌐', Colors.BRIGHT_CYAN, 'API'),
    'EVENT': LogStyle('📨', Colors.BRIGHT_YELLOW, 'EVENT'),
    'TASK': LogStyle('⚙️ ', Colors.WHITE, 'TASK'),
    'USER': LogStyle('👤', Colors.BRIGHT_MAGENTA, 'USER'),
    'NETWORK': LogStyle('🔌', Colors.CYAN, 'NETWORK'),
    'SECURITY': LogStyle('🔒', Colors.YELLOW, 'SECURITY'),
}


class SexyFormatter(logging.Formatter):
    """Formateador personalizado que añade colores y emojis a los logs."""

    def __init__(self, use_colors: bool = True, show_time: bool = True, show_name: bool = True):
        super().__init__()
        self.use_colors = use_colors
        self.show_time = show_time
        self.show_name = show_name

    def format(self, record: logging.LogRecord) -> str:
        """Formatea el registro de log con colores y emojis."""
        # Obtener el estilo para este nivel/tipo de log
        style_name = getattr(record, 'style_name', record.levelname)
        style = STYLES.get(style_name, STYLES['INFO'])

        # Construir el mensaje
        parts = []

        # Agregar timestamp si está habilitado
        if self.show_time:
            timestamp = datetime.now().strftime('%H:%M:%S')
            time_str = f"{Colors.DIM}{timestamp}{Colors.RESET}" if self.use_colors else timestamp
            parts.append(time_str)

        # Agregar prefijo con emoji y color
        if self.use_colors:
            parts.append(style.format_prefix())
        else:
            parts.append(f"{style.emoji} {style.name}")

        # Agregar nombre del logger si está habilitado
        if self.show_name:
            name_str = f"{Colors.DIM}[{record.name}]{Colors.RESET}" if self.use_colors else f"[{record.name}]"
            parts.append(name_str)

        # Agregar el mensaje
        message = record.getMessage()
        parts.append(message)

        # Unir todas las partes
        formatted = " ".join(parts)

        # Agregar información de excepción si existe
        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)

        return formatted


class SexyLogger:
    """
    Logger mejorado con soporte para logs coloridos y emojis.

    Uso:
        logger = SexyLogger(__name__)
        logger.info("Mensaje informativo")
        logger.success("Operación exitosa")
        logger.startup("Bot iniciando...")
    """

    def __init__(
        self,
        name: str = __name__,
        level: int = logging.INFO,
        use_colors: bool = True,
        show_time: bool = True,
        show_name: bool = True
    ):
        """
        Inicializa el sexy logger.

        Args:
            name: Nombre del logger
            level: Nivel de logging (logging.DEBUG, logging.INFO, etc.)
            use_colors: Si usar colores o no
            show_time: Si mostrar timestamp
            show_name: Si mostrar el nombre del logger
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Evitar duplicar handlers
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = SexyFormatter(
                use_colors=use_colors,
                show_time=show_time,
                show_name=show_name
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

            # Evitar que los logs se propaguen al logger raíz
            self.logger.propagate = False

    def _log(self, level: int, message: str, style_name: Optional[str] = None, **kwargs):
        """Método interno para hacer log con un estilo personalizado."""
        extra = kwargs.get('extra', {})
        if style_name:
            extra['style_name'] = style_name
        kwargs['extra'] = extra
        self.logger.log(level, message, **kwargs)

    # Métodos estándar
    def debug(self, message: str, **kwargs):
        """Log de debug."""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log informativo."""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log de advertencia."""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log de error."""
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log crítico."""
        self._log(logging.CRITICAL, message, **kwargs)

    # Métodos personalizados con estilos especiales
    def startup(self, message: str, **kwargs):
        """Log de inicio de sistema."""
        self._log(logging.INFO, message, style_name='STARTUP', **kwargs)

    def shutdown(self, message: str, **kwargs):
        """Log de apagado de sistema."""
        self._log(logging.INFO, message, style_name='SHUTDOWN', **kwargs)

    def success(self, message: str, **kwargs):
        """Log de operación exitosa."""
        self._log(logging.INFO, message, style_name='SUCCESS', **kwargs)

    def database(self, message: str, **kwargs):
        """Log de operaciones de base de datos."""
        self._log(logging.INFO, message, style_name='DATABASE', **kwargs)

    def api(self, message: str, **kwargs):
        """Log de operaciones de API."""
        self._log(logging.INFO, message, style_name='API', **kwargs)

    def event(self, message: str, **kwargs):
        """Log de eventos."""
        self._log(logging.INFO, message, style_name='EVENT', **kwargs)

    def task(self, message: str, **kwargs):
        """Log de tareas."""
        self._log(logging.INFO, message, style_name='TASK', **kwargs)

    def user(self, message: str, **kwargs):
        """Log de acciones de usuario."""
        self._log(logging.INFO, message, style_name='USER', **kwargs)

    def network(self, message: str, **kwargs):
        """Log de operaciones de red."""
        self._log(logging.INFO, message, style_name='NETWORK', **kwargs)

    def security(self, message: str, **kwargs):
        """Log de seguridad."""
        self._log(logging.WARNING, message, style_name='SECURITY', **kwargs)

    def set_level(self, level: int):
        """Cambia el nivel de logging."""
        self.logger.setLevel(level)


# Crear instancia global que puede ser importada directamente
logger = SexyLogger(__name__)


def get_logger(name: str, **kwargs) -> SexyLogger:
    """
    Factory function para crear loggers con configuración personalizada.

    Args:
        name: Nombre del logger
        **kwargs: Argumentos adicionales para SexyLogger

    Returns:
        Una instancia de SexyLogger configurada
    """
    return SexyLogger(name, **kwargs)
