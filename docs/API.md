# API y Servicios

## Servicios del Bot

### SubscriptionService

El servicio de suscripciones gestiona todo lo relacionado con tokens VIP y suscripciones de usuarios.

#### Funciones Principales

- **generate_vip_token(session, admin_id, tier_id, bot)**
  - Genera un token de suscripción VIP único
  - Retorna un enlace de invitación con el token

- **validate_token(session, token_str)**
  - Valida si un token es válido y no ha sido usado
  - Retorna el objeto de token si es válido

- **register_subscription(session, user_id, token_id)**
  - Registra una nueva suscripción VIP usando un token
  - Marca el token como usado y crea registro de suscripción

- **check_subscription_status(session, user_id)**
  - Verifica si un usuario tiene una suscripción activa
  - Retorna booleano

- **redeem_token(session, user_id, token_str)**
  - Canjea un token VIP para un usuario
  - Retorna resultado con éxito o error

- **send_token_redemption_success(message, tier, session)**
  - Envía mensaje de éxito y enlace de invitación al canal VIP
  - Genera un enlace de invitación único con límite de uso

- **get_active_vips_paginated(page, page_size, session)**
  - Obtiene lista paginada de suscriptores VIP activos
  - Parámetros: `page` (número de página, 1-indexed), `page_size` (tamaño de página), `session` (sesión de base de datos)
  - **Retorna**:
    ```python
    (
      List[UserSubscription],  # Lista de suscriptores para la página actual
      int                      # Total de suscriptores VIP activos
    )
    ```

- **revoke_vip_access(user_id, bot, session)**
  - Revoca el acceso VIP de un usuario expulsándolo del canal y actualizando su estado
  - Parámetros: `user_id` (ID del usuario a revocar), `bot` (instancia del bot para expulsión), `session` (sesión de base de datos)
  - **Retorna**:
    ```python
    {
      "success": boolean,
      "message": string (si éxito) / "error": string (si error)
    }
    ```

### ChannelManagementService

Gestiona las solicitudes de acceso a canales y estadísticas.

#### Funciones Principales

- **register_free_request(session, user_id)**
  - Registra una nueva solicitud de acceso gratuito
  - Retorna el objeto de solicitud

- **get_pending_requests(session)**
  - Obtiene todas las solicitudes pendientes de canal gratuito
  - Retorna lista de objetos de solicitud

- **get_channel_stats(session, channel_type)**
  - Obtiene estadísticas para un tipo de canal específico
  - Parámetros: `channel_type` ("vip" o "general")
  - **Retorna para VIP**:
    ```python
    {
      "active_subscribers": int
    }
    ```
  - **Retorna para General**:
    ```python
    {
      "total_requests": int,
      "pending_requests": int
    }
    ```

- **register_channel_id(channel_type, raw_id, bot, session)**
  - Registra IDs de canales VIP o gratuito
  - Verifica que el bot sea administrador del canal
  - Parámetros: `channel_type` ("vip", "free"), `raw_id`, `bot`, `session`
  - **Retorna**:
    ```python
    {
      "success": boolean,
      "channel_id": int (si éxito),
      "error": string (si error)
    }
    ```

- **request_free_access(session, user_id)**
  - Maneja la solicitud de acceso gratuito de un usuario
  - **Retorna para solicitud existente**:
    ```python
    {
      "status": "already_requested",
      "remaining_minutes": float,
      "wait_minutes": int
    }
    ```
  - **Retorna para nueva solicitud**:
    ```python
    {
      "status": "queued",
      "wait_minutes": int
    }
    ```

- **broadcast_post(target_channel_type, message_id, from_chat_id, use_reactions, bot, session)**
  - Envía una publicación al canal objetivo con reacciones opcionales
  - Parámetros: `target_channel_type` ("vip", "free"), `message_id`, `from_chat_id`, `use_reactions`, `bot`, `session`
  - **Retorna**:
    ```python
    {
      "success": boolean,
      "message_id": int (si éxito),
      "error": string (si error)
    }
    ```

### ConfigService

Gestiona la configuración global del bot con caché en memoria.

#### Funciones Principales

- **get_bot_config(session)**
  - Obtiene la configuración del bot (crea una si no existe)
  - Utiliza caché en memoria para mejorar rendimiento

- **update_config(session, field, value)**
  - Actualiza un campo específico de configuración
  - Retorna la configuración actualizada

- **clear_cache()**
  - Limpia la caché de configuración

- **create_tier(session, name, duration_days, price_usd)**
  - Crea una nueva tarifa de suscripción
  - Verifica que no exista una tarifa con el mismo nombre

- **get_all_tiers(session)**
  - Obtiene todas las tarifas de suscripción activas

- **get_tier_by_id(session, tier_id)**
  - Obtiene una tarifa específica por ID

- **update_tier(session, tier_id, **kwargs)**
  - Actualiza campos de una tarifa existente

- **delete_tier(session, tier_id)**
  - Marca una tarifa como inactiva (soft delete)

- **update_wait_time(minutes, session)**
  - Actualiza el tiempo de espera para solicitudes gratuitas
  - **Retorna**:
    ```python
    {
      "success": true,
      "wait_time_minutes": int
    }
    ```
    ó
    ```python
    {
      "success": false,
      "error": string
    }
    ```

- **setup_reactions(channel_type, reactions_str, session)**
  - Configura las reacciones inline para un tipo de canal
  - **Parámetros**: `channel_type` ("vip", "free"), `reactions_str`, `session`
  - **Retorna**: Lista de emojis configurados

- **get_reactions_for_channel(session, channel_type)**
  - Obtiene la lista de reacciones para un tipo de canal específico
  - **Parámetros**: `session`, `channel_type` ("vip", "free")
  - **Retorna**: Lista de reacciones para el tipo de canal especificado

- **get_config_status(session)**
  - Obtiene un resumen del estado de configuración del bot para propósitos de diagnóstico
  - **Parámetros**: `session` (sesión de base de datos)
  - **Retorna**:
    ```python
    {
      "vip_channel_id": int (ID del canal VIP configurado) / None,
      "free_channel_id": int (ID del canal Free configurado) / None,
      "wait_time_minutes": int (tiempo de espera configurado),
      "active_tiers_count": int (número de tarifas activas),
      "vip_reactions": list (lista de reacciones para canal VIP) / [],
      "free_reactions": list (lista de reacciones para canal Free) / []
    }
    ```

## Utilidades de UI

### MenuFactory

Clase para crear componentes de interfaz de usuario estandarizados.

#### Funciones Principales

- **create_reaction_keyboard(channel_type, reactions_list)**
  - Crea un teclado inline con botones de reacción para posts
  - Parámetros: `channel_type` ("vip", "free"), `reactions_list` (lista de emojis)
  - Retorna: `InlineKeyboardMarkup` con botones de reacción en una sola fila

- **create_pagination_keyboard(current_page, total_pages, callback_prefix)**
  - Crea un teclado inline con controles de paginación
  - Parámetros: `current_page` (página actual, 1-indexed), `total_pages` (número total de páginas), `callback_prefix` (prefijo para datos de callback)
  - Retorna: `List[InlineKeyboardButton]` con botones de navegación (anterior, info de página, siguiente)

## Interacciones con la API de Telegram

### Aiogram

El bot utiliza [Aiogram 3](https://docs.aiogram.dev/) para interactuar con la API de Telegram.

#### Clientes y Funcionalidades

- **Bot**: Cliente principal para enviar mensajes y realizar acciones
- **Message**: Objetos de mensaje para recibir y responder a usuarios
- **CallbackQuery**: Objetos para manejar interacciones con botones inline
- **InlineKeyboardBuilder**: Constructor de teclados inline para menús

#### Funciones Específicas de la API

- **create_chat_invite_link(chat_id, member_limit, expire_date)**
  - Crea enlaces de invitación únicos para canales
  - Usado para entregar acceso temporal a canales VIP
  - `member_limit=1` para enlaces de un solo uso

- **get_chat_member(chat_id, user_id)**
  - Verifica el estado de miembro en un chat
  - Usado para confirmar que el bot es administrador de un canal

- **me()**
  - Obtiene información sobre el bot
  - Usado para obtener el nombre de usuario del bot para crear enlaces

## Manejo de Errores

### Excepciones Personalizadas

Definidas en `bot/services/exceptions.py`:

- **ServiceError**: Error general en servicios
- **TokenInvalidError**: Token inválido o malformado
- **TokenNotFoundError**: Token no encontrado en base de datos
- **SubscriptionError**: Error en operaciones de suscripción
- **ConfigError**: Error en operaciones de configuración

### Tratamiento de Errores de Telegram

- **TelegramBadRequest**: Errores devueltos por la API de Telegram
- Manejo específico para "message is not modified" en ediciones de mensajes

## Bases de Datos

### SQLAlchemy ORM

- Conexión asíncrona a base de datos (SQLite por defecto)
- Sesiones gestionadas por middleware DBSessionMiddleware
- Transacciones manuales con rollback en caso de error
- Caché de configuración para reducir consultas

### Modelos de Base de Datos

Ver [Modelos](MODELS.md) para detalles completos de los modelos de datos.