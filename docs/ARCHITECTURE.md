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
- El servicio `GamificationService` implementa `_check_rank_up` que detecta subidas de rango y llama a `_deliver_rewards` para entregar recompensas configuradas

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

## Sistema de Entrega Automática de Recompensas

Implementado para entregar recompensas configuradas a usuarios cuando suben de rango:

- **_deliver_rewards**: Método central en GamificationService que procesa y entrega recompensas configuradas para un rango
- **Entrega VIP**: Sistema automático que extiende la suscripción VIP de un usuario al subir de rango
  - Llama a `subscription_service.add_vip_days` para añadir días configurados como recompensa
  - Envía notificación "vip_reward" con información sobre los días añadidos y nueva fecha de expiración
  - Maneja diferentes estados de suscripción (activa, expirada, sin suscripción previa)
- **Entrega de Pack de Contenido**: Sistema automático que envía archivos multimedia como recompensa al subir de rango
  - Recupera archivos asociados al pack configurado para el rango
  - Clasifica archivos en álbum (fotos y videos) e individuales (documentos, otros tipos)
  - Envía álbumes usando `send_media_group` y archivos individuales usando métodos específicos
  - Envía notificación "pack_reward" con nombre del pack y rango alcanzado
- **Integración con _check_rank_up**: El método de verificación de subida de rango ahora llama a `_deliver_rewards` cuando se detecta una subida
- **Notificaciones de Recompensas**: Plantillas específicas para notificar recompensas entregadas
  - **vip_reward**: Notificación cuando se otorgan días VIP como recompensa por subir de rango
  - **pack_reward**: Notificación cuando se otorga un pack de contenido como recompensa por subir de rango
- **Manejo de Errores**: Implementación de manejo específico para errores en envío de recompensas sin afectar el flujo principal de gamificación
- **Clasificación de Medios**: Sistema inteligente que clasifica archivos multimedia para envío apropiado como álbum o archivos individuales

## Sistema de Recompensa Diaria

Implementado para fomentar la participación diaria de los usuarios:

- **last_daily_claim**: Nuevo campo en el modelo GamificationProfile para rastrear la última reclamación diaria de cada usuario
- **claim_daily_reward**: Método en GamificationService que implementa la lógica de cooldown de 24 horas
  - Verifica si ha pasado al menos 24 horas desde la última reclamación
  - Otorga 50 puntos fijos por cada check-in diario exitoso
  - Actualiza la fecha de última reclamación en el perfil del usuario
  - Maneja adecuadamente casos de cooldown con cálculo preciso del tiempo restante
- **Notificaciones de Recompensa Diaria**: Plantillas específicas para notificar el estado de las recompensas diarias
  - **daily_success**: Notificación cuando el usuario reclama su recompensa diaria exitosamente
  - **daily_cooldown**: Notificación cuando el usuario intenta reclamar antes de que haya pasado el cooldown de 24 horas
- **Handler /daily**: Comando en el handler de usuarios que permite a los usuarios reclamar su recompensa diaria
  - Interactúa con GamificationService para procesar la reclamación
  - Envía notificaciones personalizadas según el resultado de la operación
  - Maneja adecuadamente la creación de perfiles nuevos si el usuario no tiene uno existente

## Sistema de Referidos

Implementado para fomentar la adquisición de nuevos usuarios a través de referidos:

- **referred_by_id**: Nuevo campo en el modelo GamificationProfile que almacena el ID del usuario que invitó al nuevo usuario
- **referrals_count**: Nuevo campo en el modelo GamificationProfile que cuenta el número de referidos exitosos para cada usuario
- **get_referral_link**: Método en GamificationService que genera un enlace de referido único para cada usuario
  - Recibe el ID del usuario y el nombre de usuario del bot
  - Retorna un enlace con el formato `https://t.me/{bot_username}?start=ref_{user_id}`
- **process_referral**: Método en GamificationService que procesa las referencias cuando un nuevo usuario se une usando un enlace de referido
  - Verifica que el payload tenga el formato correcto ("ref_...")
  - Extrae el ID del referidor del payload
  - Verifica que el nuevo usuario sea realmente nuevo (no tenga perfil de gamificación existente)
  - Previene bucles de referidos (auto-referidos)
  - Verifica que el referidor exista en la base de datos
  - Crea un nuevo perfil de gamificación para el nuevo usuario con el campo `referred_by_id` establecido
  - Incrementa el contador de referidos del referidor y le otorga 100 puntos
  - Otorga 50 puntos al nuevo usuario como incentivo
  - Envía notificaciones al referidor y al nuevo usuario sobre las recompensas
  - Implementa manejo de errores con rollback de base de datos en caso de fallo
- **Handler /invite**: Comando en el handler de usuarios que permite a los usuarios obtener su enlace de referido
  - Genera el enlace de referido usando el método `get_referral_link`
  - Muestra estadísticas de referidos (número de referidos exitosos)
  - Envía notificación con información sobre las recompensas por referidos
- **Integración con /start**: El handler de comandos `/start` ahora también maneja enlaces de referidos
  - Extrae el payload de referido del argumento del comando
  - Procesa la referida independientemente del redención de tokens VIP
  - Permite que un usuario se una a través de un enlace de referido y canjee un token en la misma interacción
- **Notificaciones de Referidos**: Plantillas específicas para notificar sobre referidos exitosos
  - **referral_success**: Notificación enviada al referidor cuando alguien se une a través de su enlace
  - **referral_bonus**: Notificación enviada al nuevo usuario cuando se une a través de un enlace de referido
- **Protección contra fraude**: Implementación de validaciones para prevenir abusos del sistema de referidos
  - Sistema anti-bucle que previene auto-referidos
  - Verificación de que solo usuarios nuevos puedan ser referidos
  - Validación de formato correcto del payload de referido

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

## Wizard Engine

Implementado para proporcionar una arquitectura flexible y reutilizable para flujos de interacción complejos con los usuarios:

### 3-Layer Architecture

#### 1. Core Layer (`bot/wizards/`)
- **Core Components**: Definiciones de base para contextos, pasos y wizards
  - `WizardContext`: Almacena el estado actual de un wizard activo (ID, paso actual, datos recolectados)
  - `WizardStep`: Define un paso individual con proveedores de texto, teclado, validadores y callbacks
  - `BaseWizard`: Clase base abstracta que define la estructura de un wizard
- **Validators**: Validadores comunes reutilizables para diferentes tipos de entrada
- **UI Renderer**: Componentes para generar interfaces de usuario estándar (por ejemplo, teclados Sí/No)

#### 2. Service Layer (`bot/services/wizard_service.py`)
- **WizardService**: Servicio central que gestiona la ejecución de wizards
  - Gestión de sesiones activas de wizards por usuario
  - Procesamiento de entrada de texto y callbacks
  - Validación y transición entre pasos
  - Manejo de completado y limpieza de contexto
  - Integración con el sistema de inyección de dependencias (services container)
- **State Management**: Integración con FSM de Aiogram para persistencia de estado

#### 3. Presentation Layer (`bot/handlers/wizard_handler.py`)
- **Generic Handlers**: Manejadores genéricos que pueden trabajar con cualquier wizard implementado
  - `handle_wizard_message`: Procesa entradas de texto durante wizards activos
  - `handle_wizard_callback`: Procesa entradas de callback (botones inline) durante wizards activos
- **Message Routing**: Utiliza el estado FSM "wizard_active" para enrutar mensajes a los handlers correctos

### Implementación de RankWizard

- **Flujo de Creación de Rangos**: Nuevo wizard para crear rangos de gamificación de manera guiada
  - Paso 1: Ingreso del nombre del rango (validación de longitud mínima)
  - Paso 2: Ingreso de puntos mínimos requeridos (validación numérica)
  - Paso 3: Pregunta sobre recompensas VIP (Sí/No con teclado inline)
  - Paso 4: Si aplica, ingreso de días VIP (validación numérica)
- **Integración con GamificationService**: Al completar el wizard, crea el rango en la base de datos
- **Handler de Inicio**: Nuevo handler `start_rank_creation_wizard` en admin.py para iniciar el wizard

### Beneficios del Wizard Engine

- **Modularidad**: Fácil creación de nuevos wizards sin duplicar lógica de manejo de estado
- **Reutilización**: Componentes compartidos para validación, UI y manejo de estado
- **Flexibilidad**: Soporte para pasos condicionales y lógica de negocio personalizada
- **Consistencia**: Experiencia de usuario uniforme para flujos interactivos
- **Integración**: Se integra completamente con el sistema de servicios y base de datos existente
- **Escalabilidad**: Arquitectura en capas permite extender funcionalidades sin afectar otras partes del sistema

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
- **PR24**: Mejora del manejo de excepciones con manejo específico de `TelegramAPIError` para errores de la API de Telegram

### Estructura de Importación
- Organización de importaciones siguiendo estilo PEP 8
- Agrupación lógica de dependencias estándar, terceros y locales

### Optimización de Consultas
- **PR23**: Mejora de la eficiencia de la consulta en `_check_rank_up` con `limit(1)` para evitar cargar más resultados de los necesarios
- **PR23**: Uso de SQLAlchemy ORM en la función `seed_ranks` para inicializar datos de manera más eficiente

### Limpieza de Código
- **PR23**: Eliminación de variables no utilizadas en `_on_reaction_added` para mejorar la claridad del código
- **PR23**: Corrección del problema de zona horaria en `GamificationProfile` usando `datetime.now(timezone.utc)`
- **PR24**: Refactorización para evitar objetos mock en la gestión de rangos para mejorar la claridad del código

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
   - **referred_by_id**: ID del usuario que invitó a este usuario (campo referido)
   - **referrals_count**: Número de referidos exitosos que este usuario ha conseguido

### Relaciones SQLAlchemy
- **PR24**: Implementación de relaciones SQLAlchemy descomentadas en modelos de base de datos para mejor integridad referencial
- Relación entre `RewardContentPack` y `RewardContentFile` con eliminación en cascada
- Relación entre `Rank` y `RewardContentPack` para recompensas de rangos
- Relación entre `GamificationProfile` y `Rank` para seguimiento de rangos de usuarios

## Sistema de Configuración Inicial Dual (Onboarding Assistant)

Implementado para facilitar la configuración inicial del bot con dos opciones: rápida y completa.

- **AdminOnboardingStates**: FSM que gestiona el flujo de configuración inicial del bot
  - `intro`: Presentación de opciones de configuración (rápida o completa)
  - `setup_vip_channel`: Espera el ID del canal VIP o mensaje reenviado
  - `setup_free_channel`: Espera el ID del canal gratuito o mensaje reenviado
  - `setup_protection`: Configuración de protección de contenido para canales
  - `setup_welcome_msg`: Espera el mensaje de bienvenida
  - `setup_gamification`: Espera la configuración de puntos diarios y por referidos
  - `setup_wait_time`: Espera el tiempo de espera en minutos
  - `create_first_tier`: Espera datos para crear la primera tarifa de suscripción (nombre, duración, precio)

- **Flujo de Configuración Rápida**:
  - Presentación de opciones de configuración (rápida vs completa)
  - Configuración de canales VIP y gratuito
  - Configuración del tiempo de espera
  - Creación de la primera tarifa de suscripción
  - Finalización del proceso de configuración

- **Flujo de Configuración Completa**:
  - Presentación de opciones de configuración (rápida vs completa)
  - Configuración de canales VIP y gratuito
  - Configuración de protección de contenido para ambos canales
  - Configuración del mensaje de bienvenida
  - Configuración de puntos diarios y por referidos
  - Configuración del tiempo de espera
  - Creación de la primera tarifa de suscripción
  - Finalización del proceso de configuración

- **Integración con /start**: El handler de comandos `/start` ahora detecta si es la primera vez que un administrador accede al bot
  - Si no hay canales configurados (VIP y Free), inicia automáticamente el flujo de onboarding
  - Presenta opciones de configuración rápida o completa según las preferencias del administrador
  - Utiliza el servicio `ConfigService` para almacenar la configuración dinámica en la base de datos

- **Configuración Dinámica**: El sistema ahora utiliza valores dinámicos almacenados en la base de datos en lugar de valores hardcodeados
  - `daily_reward_points`: Puntos diarios configurables en lugar de valor fijo
  - `referral_reward_points`: Puntos por referidos configurables en lugar de valor fijo
  - `welcome_message`: Mensaje de bienvenida configurable en lugar de texto fijo

## Seguridad

- Middleware de autenticación para verificar roles de administrador
- Validación de tokens de suscripción
- Protección contra uso múltiple de tokens