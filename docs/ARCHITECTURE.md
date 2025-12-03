# Arquitectura del Proyecto

## Vista General

El bot de administración de Telegram sigue una arquitectura modular basada en capas, donde cada componente tiene responsabilidades específicas y bien definidas. La arquitectura está diseñada para facilitar la escalabilidad, mantenibilidad y pruebas.

## Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                        Telegram                        │
│                      (Usuarios)                        │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│                       Main.py                          │
│                Punto de entrada del bot                │
└─────────────────┬───────────────────────────────────────┘
                  │
    ┌─────────────▼─────────────┐
    │      Dispatcher (Aiogram) │
    │         Enrutamiento      │
    └─────────────┬─────────────┘
                  │
    ┌─────────────▼─────────────┐    ┌─────────────────────┐
    │      Routers (Handlers)   │───▶│   Middlewares       │
    │  - admin_router           │    │ - Autenticación     │
    │  - user_router            │    │ - Base de datos     │
    └───────────────────────────┘    └─────────────────────┘
                  │
    ┌─────────────▼─────────────────────────────────────────┐
    │                   Services                           │
    │  - SubscriptionService (tokens, suscripciones)       │
    │  - ChannelService (canales, solicitudes)            │
    │  - ConfigService (configuración, tarifas)           │
    │  - GamificationService (puntos, rangos)             │
    └─────────────┬─────────────────────────────────────────┘
                  │
    ┌─────────────▼─────────────────────────────────────────┐
    │                   Database                           │
    │  - SQLAlchemy ORM                                     │
    │  - Models (UserSubscription, InvitationToken, etc.) │
    │  - Base de datos (SQLite por defecto)               │
    └───────────────────────────────────────────────────────┘
```

## Componentes Principales

### 1. Capa de Presentación (Handlers)

Los handlers están ubicados en `bot/handlers/` y son responsables de procesar las interacciones con los usuarios y administradores.

- **admin.py**: Maneja comandos y callbacks de administración
- **user.py**: Maneja comandos y mensajes de usuarios regulares

### 2. Capa de Lógica de Negocio (Services)

Ubicados en `bot/services/`, estos módulos contienen la lógica de negocio:

- **subscription_service.py**: Gestión de tokens de suscripción VIP
- **channel_service.py**: Gestión de solicitudes a canales, estadísticas y envío de publicaciones
- **config_service.py**: Gestión de configuración global del bot
- **stats_service.py**: Gestión de estadísticas generales, VIP y del canal gratuito
- **gamification_service.py**: Gestión del sistema de puntos y rangos para aumentar la participación de usuarios
- **notification_service.py**: Sistema de mensajería basado en plantillas para usuarios

### 3. Capa de Persistencia (Database)

En `bot/database/` se encuentra la capa de persistencia:

- **models.py**: Definición de modelos ORM
- **base.py**: Configuración base de SQLAlchemy, incluyendo el generador de sesiones asíncronas `async_session_maker` para inyección de dependencias en servicios

### 4. Capa de Configuración

- **config.py**: Variables de entorno y configuración del bot
- **states.py**: Estados FSM para flujos de configuración

## Patrones de Diseño Implementados

### Finite State Machine (FSM)
Implementado usando Aiogram para manejar flujos de configuración como:
- Configuración de tiempos de espera
- Configuración de reacciones
- Registro de canales
- Creación de tarifas de suscripción
- Envío de publicaciones con reacciones opcionales
- Creación de packs de contenido multimedia

### Middleware
Implementado para:
- Autenticación de administradores
- Inyección de sesiones de base de datos

### Inyección de Dependencias
Implementado usando el patrón Service Container para centralizar el acceso a los servicios del bot:
- `ServiceContainer`: Contenedor central que instancia y gestiona todos los servicios como singletons
- `Services`: Tipo anotado que permite inyectar el contenedor de servicios en los manejadores de Aiogram
- `get_services_container`: Función resolvedora que extrae el ServiceContainer del contexto del manejador

### Patrón Event Bus
Implementado para desacoplar módulos y permitir comunicación entre componentes sin acoplamiento directo:
- `EventBus`: Bus de eventos asíncrono simple que permite a los componentes emitir y escuchar eventos
- `Events`: Clase de constantes que define los tipos de eventos conocidos para evitar strings mágicos
- Permite un patrón de comunicación fire-and-forget sin bloquear el flujo principal
- Los listeners se ejecutan concurrentemente y errores en un listener no afectan a otros
- El handler `process_inline_reaction` emite eventos `Events.REACTION_ADDED` al EventBus cuando los usuarios reaccionan a publicaciones
- El servicio `GamificationService` escucha el evento `Events.REACTION_ADDED` y otorga puntos automáticamente a los usuarios

### Singleton con Caché
El `ConfigService` implementa un patrón de caché en memoria para la configuración del bot.

### Servicio Compartido
El `ConfigService` incluye métodos compartidos como `get_reactions_for_channel` para evitar duplicación de código y mejorar la consistencia.

### Vista de Diagnóstico
El `ConfigService` incluye un método `get_config_status` que proporciona una vista consolidada del estado de configuración del bot. Este método es utilizado para el dashboard de estado general que muestra:
- Estado de los canales (VIP y Free): configurado o pendiente
- Número de tarifas de suscripción activas
- Tiempo de espera configurado para el canal gratuito
- Estado de las reacciones (VIP y Free): configuradas o pendientes

## Patrones de Gamificación

Implementado para aumentar la participación y retención de usuarios:

- **Rank System**: Sistema de niveles basado en puntos que permite a los usuarios progresar a través de diferentes rangos (Bronce, Plata, Oro, Platino, Diamante)
- **GamificationProfile**: Perfiles de usuarios que almacenan puntos acumulados, rango actual y fecha de última interacción
- **Recompensas por Rango**: Cada rango tiene una recompensa descriptiva que se desbloquea al alcanzarlo
- **Sistema de Recompensas Avanzado**: Los rangos ahora incluyen recompensas concretas como días de suscripción VIP y packs de contenido exclusivos
- **RewardContentPack**: Contenedores de contenido multimedia que se otorgan como recompensas al alcanzar ciertos rangos
- **RewardContentFile**: Archivos individuales (fotos, videos, documentos) que forman parte de los packs de contenido
- **Relación entre Rangos y Recompensas**: Los modelos Rank incluyen campos para especificar días VIP y packs de contenido como recompensas
- **Notificaciones de Gamificación**: Sistema de notificaciones específicas para eventos de gamificación como bienvenida a la gamificación, actualizaciones de puntaje y recompensas desbloqueadas
- **Plantilla "rank_up"**: **NUEVO** - Notificación específica cuando un usuario sube de rango, mostrando el rango anterior y el nuevo rango
- **Seed Data**: Inicialización automática de rangos predeterminados en la base de datos
- **GamificationService**: Servicio central que gestiona la lógica de puntos, rangos y notificaciones de gamificación
- **Integración con Event Bus**: El servicio se suscribe al evento `Events.REACTION_ADDED` para otorgar puntos automáticamente cuando los usuarios reaccionan a publicaciones
- **Sistema de Notificaciones Automáticas**: Cuando un usuario sube de rango, se envía automáticamente una notificación personalizada usando el servicio de notificaciones

## Sistema de Gestión de Packs de Contenido

Implementado para administrar contenido multimedia como recompensas en el sistema de gamificación:

- **ContentPackCreationStates**: Estados FSM para el flujo de creación de packs de contenido multimedia
  - `waiting_pack_name`: Espera el nombre único del pack de contenido
  - `waiting_media_files`: Bucle para subir múltiples archivos multimedia (fotos, videos, documentos)
- **GamificationService Methods**: Funciones específicas para la gestión de packs de contenido
  - `create_content_pack`: Crea un nuevo pack de contenido con un nombre único
  - `add_file_to_pack`: Añade archivos multimedia a un pack existente
  - `get_all_content_packs`: Recupera todos los packs de contenido disponibles
  - `delete_content_pack`: Elimina un pack y todos sus archivos asociados
- **Media Upload Support**: Soporte para múltiples tipos de medios
  - Fotos: Formato JPG, PNG u otros formatos compatibles
  - Videos: Formato MP4 u otros formatos compatibles
  - Documentos: Cualquier tipo de archivo compatible con Telegram
- **Return Context Infrastructure**: Sistema para mantener el contexto de navegación en flujos anidados
  - Almacenamiento de contexto de retorno en el estado FSM
  - Posibilidad de regresar al punto de origen después de la creación
- **Integración con Menú VIP**: Opción "Packs de Recompensas" en el menú de administración VIP
  - Acceso directo a la gestión de packs de contenido
  - Visualización de packs existentes
  - Creación de nuevos packs

## Sistema de Gestión de Rangos y Recompensas

Implementado para administrar recompensas asociadas a los rangos de gamificación:

- **RankConfigStates**: Estados FSM para el flujo de configuración de recompensas de rangos
  - `waiting_vip_days`: Espera el número de días VIP que se otorgan como recompensa
- **GamificationService Methods**: Funciones específicas para la gestión de rangos y recompensas
  - `get_all_ranks`: Recupera todos los rangos disponibles
  - `update_rank_rewards`: Actualiza las recompensas (días VIP y packs de contenido) asociadas a un rango
  - `get_rank_by_id`: Recupera un rango específico por su ID
- **Integración con Menú VIP**: Opción "Rangos" en el menú de administración VIP
  - Acceso directo a la gestión de rangos y recompensas
  - Visualización de rangos existentes con puntos mínimos
  - Edición de recompensas por rango
- **Configuración de Recompensas**: Sistema para asignar recompensas a rangos
  - Asignación de días de suscripción VIP como recompensa
  - Asignación de packs de contenido como recompensa
  - Visualización de recompensas actuales en la edición de rangos
- **Flujo de Creación Anidada**: Sistema para crear packs de contenido directamente desde la configuración de rangos
  - Opción para crear nuevo pack desde la interfaz de edición de rango
  - Mantenimiento del contexto de navegación para regresar al rango después de crear pack
  - Sistema de "return context" para mantener el flujo lógico de navegación
- **Modelo Rank Mejorado**: Campo adicional en el modelo Rank para almacenar recompensas
  - `reward_vip_days`: Número de días VIP otorgados como recompensa
  - `reward_content_pack_id`: ID del pack de contenido otorgado como recompensa (relación con RewardContentPack)

## Mejoras de Código

### Seguridad de Tipos
- Anotaciones de tipo completas en todos los servicios y handlers
- Uso de TypedDict para estructuras de retorno
- Validación de tipos en tiempo de ejecución
- **PR23**: Implementación de constantes para valores fijos en GamificationService (como POINTS_PER_REACTION)

### Manejo de Errores
- Implementación de jerarquía de excepciones personalizadas
- Manejo específico de errores de base de datos y API de Telegram
- Mejora en la retroalimentación de errores al usuario
- **PR23**: Mejoras en el manejo de errores con SQLAlchemyError y manejo de excepciones más robusto en GamificationService
- **PR23**: Manejo específico de errores de TelegramAPIError en NotificationService

### Estructura de Importación
- Organización de importaciones siguiendo estilo PEP 8
- Agrupación lógica de dependencias estándar, terceros y locales

### Optimización de Consultas
- **PR23**: Mejora de la eficiencia de la consulta en `_check_rank_up` con `limit(1)` para evitar cargar más resultados de los necesarios
- **PR23**: Uso de SQLAlchemy ORM en la función `seed_ranks` para inicializar datos de manera más eficiente

### Limpieza de Código
- **PR23**: Eliminación de variables no utilizadas en `_on_reaction_added` para mejorar la claridad del código
- **PR23**: Corrección del problema de zona horaria en `GamificationProfile` usando `datetime.now(timezone.utc)`

## Base de Datos

### Modelos

1. **BotConfig**: Configuración general del bot
   - IDs de canales VIP y gratuitos
   - Tiempos de espera
   - Reacciones configuradas

2. **UserSubscription**: Información de suscripciones de usuarios
   - Roles (free, vip, admin)
   - Fechas de inicio y expiración
   - Estado de la suscripción

3. **InvitationToken**: Tokens de invitación para acceso VIP
   - Token único
   - ID de quién lo generó
   - Fecha de creación y uso

4. **SubscriptionTier**: Tarifas de suscripción
   - Nombre de la tarifa
   - Duración en días
   - Precio en USD

5. **FreeChannelRequest**: Solicitudes de acceso gratuito
   - ID de usuario que solicitó
   - Fecha de solicitud
   - Estado de procesamiento

6. **Rank**: Sistema de gamificación - Rangos
   - Nombre del rango (ej: "Bronce", "Plata", "Oro")
   - Puntos mínimos necesarios para alcanzarlo
   - Descripción de la recompensa asociada
   - Índice para búsquedas rápidas por puntos

7. **GamificationProfile**: Perfil de gamificación de usuarios
   - ID de usuario (Telegram ID)
   - Puntos acumulados
   - Rango actual del usuario
   - Fecha de última interacción
   - **PR23**: Corrección de la zona horaria en `last_interaction_at` usando `datetime.now(timezone.utc)`

## Seguridad

- Middleware de autenticación para verificar roles de administrador
- Validación de tokens de suscripción
- Protección contra uso múltiple de tokens