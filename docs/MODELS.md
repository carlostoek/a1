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

## Relaciones

### UserSubscription ↔ InvitationToken
- Relación de uno a muchos (una suscripción puede estar ligada a un token)
- `UserSubscription.token_id` → `InvitationToken.id`

### InvitationToken ↔ SubscriptionTier
- Relación de uno a muchos (muchos tokens pueden pertenecer a una tarifa)
- `InvitationToken.tier_id` → `SubscriptionTier.id`

## Validaciones y Restricciones

### Validaciones de Integridad
- `UserSubscription.user_id`: Único para evitar múltiples registros por usuario
- `InvitationToken.token`: Único para evitar duplicados
- `SubscriptionTier.name`: Único para evitar tarifas con mismo nombre

### Índices
- Se han definido índices en campos de consulta frecuente para optimizar rendimiento
- Índices compuestos para consultas con múltiples condiciones

## Zonas Horarias

- Todas las fechas se almacenan en UTC para consistencia
- Se utiliza `datetime.now(timezone.utc)` para obtener la fecha actual en UTC
- Las fechas se convierten a objetos timezone-aware cuando es necesario para comparaciones