# API y Servicios

## Servicios del Bot

### ServiceContainer

Contenedor central de inyección de dependencias que gestiona todos los servicios del bot como singletons.

### GamificationService

El servicio de gamificación gestiona el sistema de puntos y rangos para aumentar la participación de los usuarios.

#### Constructor

- **__init__(session_maker, event_bus, notification_service)**
  - Inicializa el servicio de gamificación con las dependencias necesarias
  - Parámetros:
    - `session_maker`: Generador de sesiones de base de datos asíncronas
    - `event_bus`: Instancia del bus de eventos para escuchar eventos
    - `notification_service`: Servicio de notificaciones para enviar mensajes a usuarios
  - **Constants**:
    - `POINTS_PER_REACTION`: Constante que define cuántos puntos se otorgan por reacción (10 puntos)

#### Funciones Principales

- **setup_listeners()**
  - Registra los listeners para eventos relevantes (por ejemplo, `Events.REACTION_ADDED`)
  - No recibe parámetros
  - No retorna valor

- **add_points(user_id, amount, session)**
  - Añade puntos a un usuario y verifica si subió de rango
  - Parámetros:
    - `user_id`: ID de Telegram del usuario
    - `amount`: Cantidad de puntos a añadir
    - `session`: Sesión de base de datos activa
  - No retorna valor
  - Implementa mejoras de manejo de errores con SQLAlchemyError y rollback en caso de error

- **_on_reaction_added(event_name, data)**
  - Maneja el evento de reacción añadida, otorgando puntos al usuario
  - Parámetros:
    - `event_name`: Nombre del evento (debería ser `Events.REACTION_ADDED`)
    - `data`: Diccionario con datos del evento, incluyendo 'user_id', 'channel_id', 'emoji'
  - No retorna valor
  - Remueve variables no utilizadas (`channel_id`, `emoji`) para mejorar la limpieza del código

- **_check_rank_up(profile, session)**
  - Verifica si el perfil de usuario subió de rango y actualiza si es necesario
  - Parámetros:
    - `profile`: Instancia de GamificationProfile del usuario
    - `session`: Sesión de base de datos activa
  - No retorna valor
  - **Mejora de eficiencia**: Utiliza `limit(1)` para mejorar la eficiencia de la consulta al buscar el nuevo rango

- **_notify_rank_up(user_id, old_rank_id, new_rank, session)**
  - Envía notificación al usuario cuando sube de rango
  - Parámetros:
    - `user_id`: ID de Telegram del usuario
    - `old_rank_id`: ID del rango anterior (puede ser None)
    - `new_rank`: Instancia del nuevo rango alcanzado
    - `session`: Sesión de base de datos activa
  - No retorna valor
  - Implementa mejoras de manejo de errores con SQLAlchemyError y manejo de casos donde no se encuentra el rango anterior

### NotificationService

#### Propiedades de Acceso Rápido

- **config**: Acceso al servicio de Configuración (`ConfigService`)
- **notify**: Acceso al servicio de Notificaciones (`NotificationService`)
- **subs**: Acceso al servicio de Suscripciones (`SubscriptionService`)
- **stats**: Acceso al servicio de Estadísticas (`StatsService`)
- **channel_manager**: Acceso al servicio de Gestión de Canales (`ChannelManagementService`)
- **bus**: Acceso al servicio de Event Bus (`EventBus`)
- **gamification**: Acceso al servicio de Gamificación (`GamificationService`)

#### Inyección de Dependencias

- **Services**: Tipo anotado (`Annotated[ServiceContainer, get_services_container]`) para inyectar el contenedor de servicios en manejadores de Aiogram
- **get_services_container**: Función resolvedora que extrae el ServiceContainer del contexto del manejador

### NotificationService

El servicio de notificaciones gestiona el envío de mensajes a los usuarios basados en plantillas.

#### Funciones Principales

- **send_notification(user_id, template_name, context_data=None, reply_markup=None)**
  - Envía una notificación al usuario basándose en una plantilla predefinida
  - Retorna `True` si el envío fue exitoso, `False` en caso de error
  - Parámetros:
    - `user_id`: ID del usuario destinatario
    - `template_name`: Nombre de la plantilla a usar
    - `context_data`: Datos de contexto para formatear la plantilla (opcional)
    - `reply_markup`: Teclado inline para adjuntar al mensaje (opcional)
  - Implementa mejoras de manejo de errores con manejo específico de TelegramAPIError

#### Plantillas Disponibles

- **welcome_gamification**: Mensaje de bienvenida con puntos iniciales
- **score_update**: Actualización de puntaje del usuario
- **reward_unlocked**: Notificación de recompensa desbloqueada
- **rank_up**: **NUEVO** - Notificación cuando un usuario sube de rango, mostrando el rango anterior y el nuevo rango
- **vip_expiration_warning**: Aviso de expiración de suscripción VIP
- **generic_alert**: Mensaje genérico de alerta

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

- **process_pending_requests(session, bot)**
  - Procesa todas las solicitudes pendientes de acceso gratuito aprobándolas
  - Parámetros: `session` (sesión de base de datos), `bot` (instancia del bot para enviar mensajes)
  - **Retorna**:
    ```python
    {
      "success": boolean,
      "processed_count": int,              # Número de solicitudes procesadas
      "errors": list (opcional),           # Lista de errores si ocurrieron
      "message": string                    # Mensaje resumen del procesamiento
    }
    ```

- **approve_request(request_id, session, bot)**
  - Aprueba una solicitud específica de acceso gratuito y otorga acceso al usuario
  - Parámetros: `request_id` (ID de la solicitud), `session` (sesión de base de datos), `bot` (instancia del bot para enviar mensajes)
  - **Retorna**:
    ```python
    {
      "success": boolean,
      "message": string (si éxito) / "error": string (si error)
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

- **toggle_content_protection(session, channel_type, enable)**
  - Activa o desactiva la protección de contenido para un tipo de canal específico
  - **Parámetros**:
    - `session` (sesión de base de datos)
    - `channel_type` ("vip" o "free")
    - `enable` (booleano para activar o desactivar la protección)
  - **Retorna**:
    ```python
    {
      "success": boolean,
      "channel_type": string ("vip" o "free"),
      "enabled": boolean,
      "error": string (opcional, si success es False)
    }
    ```

- **get_content_protection_status(session, channel_type)**
  - Obtiene el estado actual de la protección de contenido para un tipo de canal específico
  - **Parámetros**:
    - `session` (sesión de base de datos)
    - `channel_type` ("vip" o "free")
  - **Retorna**: booleano indicando si la protección está activada

### StatsService

Gestiona las estadísticas generales, VIP y del canal gratuito del bot.

#### Funciones Principales

- **get_general_stats(session)**
  - Obtiene estadísticas generales del bot
  - **Parámetros**: `session` (sesión de base de datos)
  - **Retorna**:
    ```python
    {
      "total_users": int,                    # Total de usuarios únicos registrados
      "active_vip": int,                     # Suscripciones VIP activas
      "expired_revoked_vip": int,            # Suscripciones VIP históricas (expiradas/revocadas)
      "tokens_generated": int,               # Tokens de invitación generados
      "total_revenue": float                 # Ingresos totales estimados (placeholder)
    }
    ```

- **get_vip_stats(session)**
  - Obtiene estadísticas de suscripciones VIP
  - **Parámetros**: `session` (sesión de base de datos)
  - **Retorna**:
    ```python
    {
      "tier_counts": dict,                   # Conteo de usuarios activos por ID de tarifa
      "tokens_redeemed": int,                # Tokens de invitación redimidos
      "tokens_expired_unused": int           # Tokens expirados/sin usar
    }
    ```

- **get_free_channel_stats(session)**
  - Obtiene estadísticas del canal gratuito
  - **Parámetros**: `session` (sesión de base de datos)
  - **Retorna**:
    ```python
    {
      "pending_count": int,                  # Solicitudes pendientes
      "processed_count": int,                # Solicitudes procesadas (histórico)
      "rejected_count": int                  # Solicitudes rechazadas/limpiadas
    }
    ```

## Servicio de Eventos (Event Bus)

### EventBus

Bus de eventos asíncrono simple para desacoplar módulos y permitir comunicación entre componentes sin acoplamiento directo.

#### Funciones Principales

- **subscribe(event_name, handler)**
  - Registra una función para escuchar un evento específico
  - Parámetros:
    - `event_name`: Nombre del evento como string
    - `handler`: Función asincrónica que manejará el evento, con firma `Callable[[str, Dict[str, Any]], Awaitable[None]]`
  - No retorna valor

- **emit(event_name, data)**
  - Publica un evento. Ejecuta todos los listeners suscritos de forma concurrente sin bloquear el flujo principal (fire-and-forget)
  - Parámetros:
    - `event_name`: Nombre del evento como string
    - `data`: Diccionario con datos a pasar al manejador
  - No retorna valor

- **_run_handler(handler, event_name, data)**
  - Wrapper seguro para ejecutar handlers y capturar errores
  - Parámetros:
    - `handler`: Función manejadora del evento
    - `event_name`: Nombre del evento
    - `data`: Diccionario con datos del evento
  - No retorna valor

#### Tipos de Eventos Disponibles (Events)

- **Events.REACTION_ADDED**: Emitido cuando alguien reacciona a una publicación
- **Events.SUBSCRIPTION_NEW**: Emitido cuando alguien compra una suscripción VIP
- **Events.VIP_EXPIRED**: Emitido cuando a alguien expira su suscripción VIP
- **Events.LEVEL_UP**: (Futuro) Emitido cuando un usuario sube de nivel

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

- **create_menu(title, options, description=None, back_callback=None, has_main=True)**
  - Crea un menú estandarizado con botones de navegación
  - Parámetros:
    - `title`: Título del menú
    - `options`: Lista de tuplas (Texto del botón, Callback data)
    - `description`: Texto opcional para mostrar sobre el título del menú
    - `back_callback`: Callback data para el botón 'Volver'. Si es None, no se muestra
    - `has_main`: Incluir botón 'Menú Principal' (callback 'admin_main_menu')
  - Retorna: `dict` con claves 'text' (str) y 'markup' (InlineKeyboardMarkup)

- **create_simple_menu(title, options)**
  - Crea un menú simple sin botones de navegación
  - Parámetros: `title` (título del menú), `options` (lista de tuplas (Texto del botón, Callback data))
  - Retorna: `dict` con claves 'text' (str) y 'markup' (InlineKeyboardMarkup)

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

## Handlers

### process_inline_reaction

Handler que procesa reacciones inline de usuarios a publicaciones en canales.

#### Función

- **process_inline_reaction(callback_query: CallbackQuery, callback_data: ReactionCallback, services: Services)**
  - Maneja las interacciones de reacción inline de los usuarios
  - Emite un evento al EventBus en lugar de procesar la reacción directamente
  - Parámetros:
    - `callback_query`: Objeto de consulta de callback de Aiogram
    - `callback_data`: Datos deserializados del callback que contienen tipo de canal y emoji
    - `services`: Contenedor de servicios inyectado para acceso a EventBus y otros servicios
  - No retorna valor
  - Responde inmediatamente al callback para eliminar el estado de carga en Telegram
  - Extrae datos de reacción (tipo de canal, emoji) de los datos del callback
  - Emite evento `Events.REACTION_ADDED` al EventBus con datos del usuario, canal, emoji y mensaje
  - Implementa el patrón de desacoplamiento entre capa de UI y lógica de negocio

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

### Modelos de Gamificación

#### Rank

Modelo que representa los rangos en el sistema de gamificación con campos de recompensas.

- **id**: Identificador único del rango
- **name**: Nombre del rango (ej: "Bronce", "Plata", "Oro", "Platino", "Diamante")
- **min_points**: Puntos mínimos necesarios para alcanzar este rango
- **reward_description**: Descripción de la recompensa asociada al rango
- **reward_vip_days**: Número de días de suscripción VIP otorgados como recompensa al alcanzar este rango
- **reward_content_pack_id**: ID del pack de contenido otorgado como recompensa al alcanzar este rango (relación con RewardContentPack)
- **Índices**: idx_rank_points para búsquedas rápidas por puntos mínimos

#### GamificationProfile

Modelo que representa el perfil de gamificación de un usuario.

- **user_id**: ID de Telegram del usuario (clave primaria)
- **points**: Puntos acumulados por el usuario
- **current_rank_id**: ID del rango actual del usuario (relación con Rank)
- **last_interaction_at**: Fecha de la última interacción del usuario
  - **Mejora**: Utiliza `datetime.now(timezone.utc)` para corregir problemas de zona horaria

### Modelos de Sistema de Recompensas

#### RewardContentPack

Modelo que representa un pack de contenido que se otorga como recompensa en el sistema de gamificación.

- **id**: Identificador único del pack de contenido
- **name**: Nombre único del pack de contenido (ej: "Pack de Bienvenida", "Set Exclusivo Octubre")
- **created_at**: Fecha de creación del pack de contenido
- **Relación**: Contiene múltiples RewardContentFile (uno a muchos)

#### RewardContentFile

Modelo que representa un archivo individual que forma parte de un pack de contenido de recompensa.

- **id**: Identificador único del archivo de contenido
- **pack_id**: ID del pack de contenido al que pertenece (relación con RewardContentPack)
- **file_id**: ID de Telegram para enviar el archivo
- **file_unique_id**: ID único para evitar duplicados
- **media_type**: Tipo de contenido ('photo', 'video', 'document')