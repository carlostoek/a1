# Documentación del Bot de Telegram

## Descripción General

Este es un bot de administración de Telegram multifuncional que permite la gestión de suscripciones VIP y acceso gratuito a canales. El bot incluye funcionalidades de administración, servicios de suscripción con tokens, configuración de canales y gestión de usuarios.

## Características Principales

- **Sistema de Suscripción VIP**: Configuración de diferentes tarifas de suscripción con duración y precios específicos
- **Acceso a Canales**: Gestión separada de canales VIP y gratuitos
- **Tokens de Invitación**: Generación y canje de tokens para acceso VIP
- **Gestión de Suscriptores VIP**: Visualización paginada de suscriptores, información detallada y revocación de acceso
- **Configuración Flexible**: Configuración de tiempos de espera, reacciones y otros parámetros
- **Interfaz de Menú**: Navegación por menús intuitivos para administradores
- **Sistema de Estados FSM**: Control de flujos de configuración con Máquina de Estados Finitos

## Arquitectura del Proyecto

```
a1/
├── bot/
│   ├── config.py          # Configuración y variables de entorno
│   ├── states.py          # Estados FSM para flujos de configuración
│   ├── tasks.py           # Tareas en segundo plano
│   ├── database/          # Componentes de base de datos
│   ├── handlers/          # Manejadores de comandos y callbacks
│   ├── middlewares/       # Middleware de autenticación y base de datos
│   ├── services/          # Lógica de negocio y servicios
│   └── utils/             # Utilidades y herramientas auxiliares
├── docs/                  # Documentación del proyecto
├── init_db.py             # Inicialización de la base de datos
├── main.py                # Punto de entrada del bot
├── requirements.txt       # Dependencias del proyecto
└── tests/                 # Pruebas unitarias e integración
```

## Tecnologías Utilizadas

- Python 3.8+
- [Aiogram 3](https://docs.aiogram.dev/) - Framework para bots de Telegram
- SQLAlchemy - ORM para base de datos
- Pydantic - Validación de configuración
- SQLite - Base de datos (por defecto)
- FSM (Finite State Machine) - Control de flujos de conversación

## Sistema de Logging (Sexy Logger)

El bot incluye un sistema de logging colorido y atractivo con emojis para mejorar la visualización de logs en la consola.

### Características del Logger

- **Logs coloridos**: Cada nivel de log tiene su propio color distintivo
- **Emojis contextuales**: Iconos visuales para identificar rápidamente el tipo de log
- **Logs personalizados**: Métodos especializados para diferentes contextos (startup, database, API, etc.)
- **Configuración flexible**: Opciones para personalizar colores, timestamps y formato
- **Compatible con logging estándar**: Basado en el módulo `logging` de Python

### Niveles de Log Disponibles

**Niveles estándar:**
- `logger.debug()` - Mensajes de depuración (🔍 cyan)
- `logger.info()` - Información general (ℹ️ azul)
- `logger.warning()` - Advertencias (⚠️ amarillo)
- `logger.error()` - Errores (❌ rojo)
- `logger.critical()` - Errores críticos (💥 fondo rojo)

**Niveles personalizados:**
- `logger.startup()` - Inicio de sistema (🚀 verde brillante)
- `logger.shutdown()` - Apagado de sistema (🛑 rojo brillante)
- `logger.success()` - Operaciones exitosas (✅ verde brillante)
- `logger.database()` - Operaciones de base de datos (🗄️ magenta)
- `logger.api()` - Llamadas API (🌐 cyan brillante)
- `logger.event()` - Eventos del sistema (📨 amarillo brillante)
- `logger.task()` - Tareas en background (⚙️ blanco)
- `logger.user()` - Acciones de usuario (👤 magenta brillante)
- `logger.network()` - Operaciones de red (🔌 cyan)
- `logger.security()` - Eventos de seguridad (🔒 amarillo)

### Uso Básico

```python
from bot.utils.sexy_logger import get_logger

# Crear una instancia del logger
logger = get_logger(__name__)

# Usar los diferentes niveles
logger.startup("Bot iniciando...")
logger.database("Conectando a la base de datos...")
logger.success("Conexión exitosa")
logger.user("Usuario @johndoe realizó login")
logger.api("Llamada API: GET /api/v1/users")
logger.error("Error al procesar solicitud")
```

### Configuración Avanzada

```python
from bot.utils.sexy_logger import SexyLogger
import logging

# Logger con configuración personalizada
logger = SexyLogger(
    name="MiModulo",
    level=logging.DEBUG,        # Nivel de logging
    use_colors=True,            # Activar/desactivar colores
    show_time=True,             # Mostrar timestamp
    show_name=True              # Mostrar nombre del logger
)

# Logger sin colores (para archivos de log)
logger_file = SexyLogger("FileLogger", use_colors=False)

# Logger minimalista
logger_minimal = SexyLogger("Minimal", show_time=False, show_name=False)
```

### Ejemplo de Salida

```
21:19:22 🚀 STARTUP [BotManager] Bot iniciando...
21:19:22 🗄️  DATABASE [BotManager] Conectando a la base de datos...
21:19:22 ✅ SUCCESS [BotManager] Conexión a DB establecida
21:19:23 🌐 API [BotManager] Validando token de Telegram API...
21:19:23 ✅ SUCCESS [BotManager] Token validado correctamente
21:19:24 👤 USER [BotManager] Usuario @alice envió comando /start
21:19:24 📨 EVENT [BotManager] Procesando evento: new_subscription
21:19:25 ⚠️  WARNING [BotManager] Cola de mensajes alcanzó el 80%
21:19:26 🛑 SHUTDOWN [BotManager] Bot apagándose correctamente
```

### Demostración

Para ver todos los estilos de logging en acción, ejecuta:

```bash
python demo_sexy_logger.py
```

Este script muestra ejemplos de todos los niveles de log, configuraciones diferentes y casos de uso comunes.

## Comandos Disponibles

### Comandos Públicos
- `/start [token]` - Iniciar conversación o canjear token VIP
- `/free` - Solicitar acceso gratuito al canal

### Comandos de Administrador
- `/admin` - Acceder al panel de administración

## Flujos de Trabajo

### Para Usuarios
1. **Acceso VIP**: Recibir token → Usar `/start TOKEN` → Obtener acceso al canal VIP
2. **Acceso Gratuito**: Usar `/free` → Esperar tiempo configurado → Recibir enlace

### Para Administradores
1. **Configuración Inicial**: Configurar canales VIP y gratuitos
2. **Gestión de Tarifas**: Crear, editar o eliminar tarifas de suscripción
3. **Generación de Tokens**: Crear tokens para distribuir a usuarios VIP
4. **Monitoreo**: Ver estadísticas de usuarios y solicitudes

## Estructura de Configuración

El bot utiliza variables de entorno definidas en `.env`:

- `BOT_TOKEN`: Token del bot de Telegram
- `ADMIN_IDS`: IDs de usuarios con permisos de administrador (JSON array o comma-separated)
- `DB_URL`: URL de conexión a la base de datos (opcional)

## Documentación Adicional

- [Arquitectura](ARCHITECTURE.md) - Estructura y diseño del sistema
- [Comandos](COMMANDS.md) - Detalles de todos los comandos y flujos
- [API y Servicios](API.md) - Interacciones y servicios del sistema
- [Gestión de Suscriptores VIP](VIP_SUBSCRIBER_MANAGEMENT.md) - Sistema de paginación y revocación de suscriptores VIP
- [Modelos](MODELS.md) - Estructura de base de datos
- [FSM](FSM.md) - Máquinas de estados para flujos de configuración
- [Servicio de Estadísticas](STATS_SERVICE.md) - Dashboard y métricas del bot
- [Envío de Publicaciones](POST_SENDING.md) - Funcionalidad de envío de posts con reacciones
- [Historial de Cambios](CHANGELOG.md) - Registro de versiones y cambios