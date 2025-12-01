# Documentación del Bot de Telegram

## Descripción General

Este es un bot de administración de Telegram multifuncional que permite la gestión de suscripciones VIP y acceso gratuito a canales. El bot incluye funcionalidades de administración, servicios de suscripción con tokens, configuración de canales y gestión de usuarios.

## Características Principales

- **Sistema de Suscripción VIP**: Configuración de diferentes tarifas de suscripción con duración y precios específicos
- **Acceso a Canales**: Gestión separada de canales VIP y gratuitos
- **Tokens de Invitación**: Generación y canje de tokens para acceso VIP
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
- [Modelos](MODELS.md) - Estructura de base de datos
- [FSM](FSM.md) - Máquinas de estados para flujos de configuración
- [Envío de Publicaciones](POST_SENDING.md) - Funcionalidad de envío de posts con reacciones
- [Historial de Cambios](CHANGELOG.md) - Registro de versiones y cambios