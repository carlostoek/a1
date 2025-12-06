# Modelos de Base de Datos

## Descripción General

El sistema utiliza SQLAlchemy ORM para mapear objetos Python a tablas de base de datos. Todos los modelos heredan de la clase base `Base` definida en `bot/database/base.py`.

## Diagrama de Relaciones

```
BotConfig (1) ←→ (N) UserSubscription
      │
      │
      ▼
SubscriptionTier (1) ←→ (N) InvitationToken (1) ←→ (N) UserSubscription
      │
      ▼
InvitationToken (N) ←→ (1) UserSubscription

FreeChannelRequest (N) - Representa solicitudes independientes
```

## Modelos Detallados

### BotConfig

**Tabla**: `bot_config`

Configuración global del bot.

| Campo | Tipo | Descripción | Valor por defecto |
|-------|------|-------------|------------------|
| id | Integer (PK) | ID de configuración | Autoincremental |
| vip_channel_id | String nullable | ID del canal VIP | None |
| free_channel_id | String nullable | ID del canal gratuito | None |
| wait_time_minutes | Integer | Tiempo de espera para acceso gratuito en minutos | 0 |
| vip_reactions | JSON | Lista de reacciones para el canal VIP | {} |
| free_reactions | JSON | Lista de reacciones para el canal gratuito | {} |
| subscription_fees | JSON | Tarifas de suscripción | {} |
| vip_content_protection | Boolean | Indica si la protección de contenido está activada para el canal VIP | False |
| free_content_protection | Boolean | Indica si la protección de contenido está activada para el canal gratuito | False |
| welcome_message | Text | Mensaje de bienvenida que ven los usuarios al usar /start | "¡Bienvenido al Bot Oficial! 🚀\nUsa /daily para tu recompensa." |
| daily_reward_points | Integer | Puntos otorgados por recompensa diaria | 50 |
| referral_reward_points | Integer | Puntos otorgados por referidos exitosos | 100 |
| content_protection_enabled | Boolean | Indica si la protección de contenido está activada globalmente | False |

### UserSubscription

**Tabla**: `user_subscriptions`

Registra las suscripciones de usuarios.

| Campo | Tipo | Descripción | Valor por defecto |
|-------|------|-------------|------------------|
| id | Integer (PK) | ID de la suscripción | Autoincremental |
| user_id | BigInteger, Unique, Index | ID de usuario en Telegram | - |
| role | String(20), Index | Rol del usuario ('free', 'vip', 'admin') | 'free' |
| join_date | DateTime | Fecha de inicio de suscripción | Fecha actual UTC |
| expiry_date | DateTime nullable | Fecha de expiración de la suscripción | None |
| status | String(20) | Estado ('active', 'expired') | 'active' |
| token_id | Integer FK | ID del token usado para suscripción | None |
| reminder_sent | Boolean | Indica si se envió recordatorio | False |

**Índices**:
- Individual: `user_id`
- Individual: `role`
- Compuesto: `status` + `expiry_date`

### InvitationToken

**Tabla**: `invitation_tokens`

Tokens de suscripción VIP generados por administradores.

| Campo | Tipo | Descripción | Valor por defecto |
|-------|------|-------------|------------------|
| id | Integer (PK) | ID del token | Autoincremental |
| token | String, Unique, Index | Valor único del token | - |
| generated_by | BigInteger | ID del administrador que generó el token | - |
| created_at | DateTime | Fecha de creación del token | Fecha actual UTC |
| tier_id | Integer FK | ID de la tarifa de suscripción asociada | - |
| used | Boolean | Indica si el token ya fue usado | False |
| used_by | BigInteger nullable | ID del usuario que usó el token | None |
| used_at | DateTime nullable | Fecha de uso del token | None |

**Índices**:
- Individual: `token`
- Individual: `used`

### SubscriptionTier

**Tabla**: `subscription_tiers`

Definición de tarifas de suscripción VIP.

| Campo | Tipo | Descripción | Valor por defecto |
|-------|------|-------------|------------------|
| id | Integer (PK) | ID de la tarifa | Autoincremental |
| name | String(50), Unique, Index | Nombre de la tarifa | - |
| duration_days | Integer | Duración en días | - |
| price_usd | Float | Precio en USD | - |
| is_active | Boolean | Indica si la tarifa está activa | True |
| created_at | DateTime | Fecha de creación de la tarifa | Fecha actual UTC |

**Índices**:
- Individual: `name`

### FreeChannelRequest

**Tabla**: `free_channel_requests`

Registra solicitudes de acceso gratuito al canal.

| Campo | Tipo | Descripción | Valor por defecto |
|-------|------|-------------|------------------|
| id | Integer (PK) | ID de la solicitud | Autoincremental |
| user_id | BigInteger, Index | ID de usuario que solicitó | - |
| request_date | DateTime | Fecha de la solicitud | Fecha actual UTC |
| processed | Boolean | Indica si la solicitud ha sido procesada | False |
| processed_at | DateTime nullable | Fecha de procesamiento | None |

**Índices**:
- Individual: `user_id`
- Compuesto: `user_id` + `request_date`

## Modelos de Sistema de Recompensas

### RewardContentPack

**Tabla**: `reward_content_packs`

Contenedor para packs de contenido que se otorgan como recompensas en el sistema de gamificación.

| Campo | Tipo | Descripción | Valor por defecto |
|-------|------|-------------|------------------|
| id | Integer (PK) | ID del pack de contenido | Autoincremental |
| name | String(100), Unique | Nombre único del pack de contenido | - |
| created_at | DateTime | Fecha de creación del pack | Fecha actual UTC |

### RewardContentFile

**Tabla**: `reward_content_files`

Archivos individuales que pertenecen a un pack de contenido de recompensa.

| Campo | Tipo | Descripción | Valor por defecto |
|-------|------|-------------|------------------|
| id | Integer (PK) | ID del archivo de contenido | Autoincremental |
| pack_id | Integer FK | ID del pack de contenido al que pertenece | - |
| file_id | String(255) | ID de Telegram para enviar el archivo | - |
| file_unique_id | String(255) | ID único para evitar duplicados | - |
| media_type | String(20) | Tipo de contenido ('photo', 'video', 'document') | - |

## Actualización del Modelo Rank

**Tabla**: `gamification_ranks`

Modelo actualizado para incluir campos de recompensas en el sistema de gamificación.

| Campo | Tipo | Descripción | Valor por defecto |
|-------|------|-------------|------------------|
| id | Integer (PK) | ID del rango | Autoincremental |
| name | String(50), Unique | Nombre del rango (ej: "Bronce", "Plata") | - |
| min_points | Integer, Unique | Puntos mínimos necesarios para alcanzar el rango | - |
| reward_description | String(200), Nullable | Descripción de la recompensa asociada | None |
| reward_vip_days | Integer | Días de suscripción VIP otorgados como recompensa | 0 |
| reward_content_pack_id | Integer FK, Nullable | ID del pack de contenido otorgado como recompensa | None |

**Índices**:
- Individual: `min_points` (idx_rank_points)

## Modelo GamificationProfile

**Tabla**: `gamification_profiles`

Modelo actualizado para incluir el sistema de gamificación con recompensas diarias.

| Campo | Tipo | Descripción | Valor por defecto |
|-------|------|-------------|------------------|
| user_id | BigInteger (PK) | ID de usuario en Telegram (clave primaria) | - |
| points | Integer | Puntos acumulados por el usuario | 0 |
| current_rank_id | Integer FK, Nullable | ID del rango actual del usuario | None |
| last_interaction_at | DateTime | Fecha de última interacción del usuario | Fecha actual UTC |
| last_daily_claim | DateTime, Nullable | Fecha de la última reclamación de recompensa diaria | None |

**Índices**:
- Individual: `user_id` (clave primaria)

## Relaciones

### UserSubscription ↔ InvitationToken
- Relación de uno a muchos (una suscripción puede estar ligada a un token)
- `UserSubscription.token_id` → `InvitationToken.id`

### InvitationToken ↔ SubscriptionTier
- Relación de uno a muchos (muchos tokens pueden pertenecer a una tarifa)
- `InvitationToken.tier_id` → `SubscriptionTier.id`

### Rank ↔ RewardContentPack
- Relación de uno a muchos (un pack de contenido puede estar asociado a múltiples rangos)
- `Rank.reward_content_pack_id` → `RewardContentPack.id`

### RewardContentPack ↔ RewardContentFile
- Relación de uno a muchos (un pack de contenido puede contener múltiples archivos)
- `RewardContentFile.pack_id` → `RewardContentPack.id`

### GamificationProfile ↔ Rank
- Relación de uno a muchos (muchos perfiles pueden estar asociados a un rango)
- `GamificationProfile.current_rank_id` → `Rank.id`

## Validaciones y Restricciones

### Validaciones de Integridad
- `UserSubscription.user_id`: Único para evitar múltiples registros por usuario
- `InvitationToken.token`: Único para evitar duplicados
- `SubscriptionTier.name`: Único para evitar tarifas con mismo nombre
- `RewardContentPack.name`: Único para evitar packs de contenido duplicados

### Índices
- Se han definido índices en campos de consulta frecuente para optimizar rendimiento
- Índices compuestos para consultas con múltiples condiciones

### Mejoras de Seguridad de PR12

- **Validación de tipos de canal**: Verificación adicional en `BotConfig` para asegurar que los tipos de canal sean válidos ('vip' o 'free')
- **Anotaciones de tipo mejoradas**: Tipos específicos para campos de reacciones y otros valores configurables
- **Manejo seguro de valores nulos**: Validación adicional para campos opcionales

## Zonas Horarias

- Todas las fechas se almacenan en UTC para consistencia
- Se utiliza `datetime.now(timezone.utc)` para obtener la fecha actual en UTC
- Las fechas se convierten a objetos timezone-aware cuando es necesario para comparaciones