# Plan de Preparación para el Módulo Narrativo

## 1. Estado Actual del Sistema

### 1.1 Arquitectura General
El sistema es un bot de Telegram construido con:
- **Framework**: aiogram 3.x con soporte asíncrono
- **Base de datos**: SQLAlchemy ORM con SQLite (aiosqlite)
- **Patrón arquitectónico**: Inyección de dependencias vía `ServiceContainer`
- **Comunicación entre módulos**: Event Bus asíncrono para desacoplamiento

### 1.2 Módulos Existentes

#### Módulo de Administración de Canales (`channel_service.py`)
- Gestión de canales VIP y Free
- Registro de IDs de canales
- Sistema de solicitudes de acceso gratuito con tiempo de espera
- Broadcast de publicaciones con reacciones opcionales
- Limpieza automática de solicitudes antiguas

#### Módulo de Gamificación (`gamification_service.py`)
- Sistema de puntos (`GamificationProfile`)
- Sistema de rangos (`Rank`) con recompensas configurables
- Recompensa diaria (`claim_daily_reward`) con cooldown de 24h
- Sistema de referidos (`process_referral`, `get_referral_link`)
- Packs de contenido como recompensas (`RewardContentPack`, `RewardContentFile`)
- Otorgamiento automático de puntos por reacciones (10 puntos por reacción)
- Entrega automática de recompensas al subir de rango (VIP days, content packs)

### 1.3 Modelos de Base de Datos Existentes

| Modelo | Propósito |
|--------|-----------|
| `BotConfig` | Configuración global del bot |
| `UserSubscription` | Suscripciones VIP de usuarios |
| `InvitationToken` | Tokens de invitación VIP |
| `SubscriptionTier` | Tarifas de suscripción |
| `FreeChannelRequest` | Solicitudes de acceso gratuito |
| `GamificationProfile` | Perfil de gamificación del usuario |
| `Rank` | Rangos con puntos mínimos y recompensas |
| `RewardContentPack` | Packs de contenido como recompensas |
| `RewardContentFile` | Archivos multimedia en packs |

### 1.4 Servicios Existentes
- `ConfigService`: Configuración del bot con cache en memoria
- `SubscriptionService`: Gestión de suscripciones VIP
- `ChannelManagementService`: Gestión de canales
- `GamificationService`: Sistema de puntos y rangos
- `NotificationService`: Notificaciones con plantillas
- `StatsService`: Estadísticas del sistema
- `EventBus`: Comunicación desacoplada entre módulos
- `WizardService`: Motor de wizards para flujos interactivos

### 1.5 Eventos Disponibles en EventBus
```python
class Events(str, Enum):
    REACTION_ADDED = "reaction_added"
    SUBSCRIPTION_NEW = "subscription_new"
    VIP_EXPIRED = "vip_expired"
    LEVEL_UP = "level_up"  # Ya definido
```

---

## 2. Qué Está Listo para el Nuevo Módulo

### 2.1 Infraestructura Sólida
- **Event Bus**: Ya implementado y funcional. El módulo narrativo puede suscribirse a eventos existentes y emitir nuevos.
- **Inyección de Dependencias**: `ServiceContainer` permite agregar nuevos servicios fácilmente.
- **Sistema de Notificaciones**: Plantillas extensibles para mensajes al usuario.
- **Motor de Wizards**: Framework para flujos interactivos complejos que puede usarse para desbloquear historias.

### 2.2 Sistema de Gamificación Base
- Ya existe el concepto de puntos en `GamificationProfile.points`
- Los rangos ya tienen estructura de recompensas (`reward_vip_days`, `reward_content_pack_id`)
- El sistema de referidos funciona y otorga puntos
- La recompensa diaria está implementada con cooldown de 24h

### 2.3 Integración con Canales
- El sistema ya detecta reacciones a publicaciones
- Emite eventos al EventBus cuando un usuario reacciona
- El `GamificationService` ya escucha el evento `REACTION_ADDED`

### 2.4 Patrones de Código Establecidos
- Handlers separados por dominio (`admin.py`, `user.py`)
- Estados FSM bien organizados en `states.py`
- UI Factory para menús consistentes
- Manejo de errores estandarizado

---

## 3. Qué Necesita Refactorización o Mejoras

### 3.1 CRÍTICO: Renombrar Sistema de Puntos a "Besitos"

**Archivos afectados:**
- `/bot/database/models.py`: Renombrar `GamificationProfile.points` a `besitos`
- `/bot/services/gamification_service.py`: Actualizar todas las referencias
- `/bot/services/notification_service.py`: Actualizar plantillas
- `/bot/handlers/user.py`: Actualizar comandos

**Consideración**: Evaluar si crear una migración de base de datos o un campo alias.

### 3.2 IMPORTANTE: Extender el Modelo GamificationProfile

El perfil actual no tiene campos para:
- Balance de moneda (besitos)
- Inventario de productos
- Pistas desbloqueadas
- Capítulos narrativos desbloqueados
- Insignias obtenidas

**Nuevo modelo sugerido:**
```python
class GamificationProfile(Base):
    # Existentes
    user_id: Mapped[int]
    points: Mapped[int]  # Renombrar a besitos
    current_rank_id: Mapped[int]

    # NUEVOS para narrativa
    story_progress: Mapped[dict] = mapped_column(JSON, default=dict)  # {"chapter_id": unlocked}
    clues_collected: Mapped[list] = mapped_column(JSON, default=list)  # ["clue_id_1", "clue_id_2"]
    badges: Mapped[list] = mapped_column(JSON, default=list)  # ["badge_id_1"]
    inventory: Mapped[dict] = mapped_column(JSON, default=dict)  # {"product_id": quantity}
```

### 3.3 IMPORTANTE: Nuevos Modelos de Base de Datos Requeridos

```python
# Productos de la Tienda
class ShopProduct(Base):
    id: Mapped[int]
    name: Mapped[str]
    description: Mapped[str]
    price_besitos: Mapped[int]
    product_type: Mapped[str]  # 'clue', 'story_unlock', 'badge_boost', etc.
    effect_data: Mapped[dict]  # JSON con datos del efecto
    is_active: Mapped[bool]
    stock: Mapped[int]  # -1 para ilimitado

# Transacciones de Tienda
class ShopTransaction(Base):
    id: Mapped[int]
    user_id: Mapped[int]
    product_id: Mapped[int]
    quantity: Mapped[int]
    total_cost: Mapped[int]
    timestamp: Mapped[datetime]

# Capítulos Narrativos
class StoryChapter(Base):
    id: Mapped[int]
    title: Mapped[str]
    content: Mapped[str]  # O referencia a media
    unlock_requirement: Mapped[str]  # 'rank:5', 'clues:3', 'product:xyz'
    order: Mapped[int]
    is_active: Mapped[bool]

# Pistas
class Clue(Base):
    id: Mapped[int]
    name: Mapped[str]
    description: Mapped[str]
    rarity: Mapped[str]  # common, rare, epic
    combinable_with: Mapped[list]  # JSON: ["clue_id_1", "clue_id_2"]
    combination_result: Mapped[str]  # 'badge:xyz', 'vip_access', 'chapter:5'

# Insignias
class Badge(Base):
    id: Mapped[int]
    name: Mapped[str]
    description: Mapped[str]
    icon: Mapped[str]  # emoji o file_id
    unlock_condition: Mapped[str]  # 'clue_combo:x,y', 'reactions:100', etc.
    reward_type: Mapped[str]  # 'vip_days', 'besitos', 'story_unlock'
    reward_value: Mapped[str]
```

### 3.4 IMPORTANTE: Nuevos Eventos para EventBus

```python
class Events(str, Enum):
    # Existentes
    REACTION_ADDED = "reaction_added"
    SUBSCRIPTION_NEW = "subscription_new"
    VIP_EXPIRED = "vip_expired"
    LEVEL_UP = "level_up"

    # NUEVOS para narrativa
    BESITOS_EARNED = "besitos_earned"
    PRODUCT_PURCHASED = "product_purchased"
    CLUE_FOUND = "clue_found"
    CLUE_COMBINED = "clue_combined"
    CHAPTER_UNLOCKED = "chapter_unlocked"
    BADGE_EARNED = "badge_earned"
    DAILY_GIFT_CLAIMED = "daily_gift_claimed"
```

### 3.5 MENOR: Configuración Global para Narrativa

Extender `BotConfig`:
```python
class BotConfig(Base):
    # Existentes...

    # NUEVOS
    daily_besitos_gift: Mapped[int] = mapped_column(Integer, default=10)
    reaction_besitos_reward: Mapped[int] = mapped_column(Integer, default=5)
    shop_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    narrative_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
```

### 3.6 MENOR: Refactorizar NotificationService

Agregar nuevas plantillas:
```python
NOTIFICATION_TEMPLATES = {
    # Existentes...

    # NUEVOS
    "besitos_earned": "💋 Ganaste {amount} besitos por {reason}. Total: {total}",
    "product_purchased": "🛒 Compraste {product_name} por {cost} besitos",
    "clue_found": "🔍 Encontraste una pista: {clue_name}",
    "chapter_unlocked": "📖 Capítulo desbloqueado: {chapter_title}",
    "badge_earned": "🏅 Insignia obtenida: {badge_name}",
    "daily_gift": "🎁 Regalo diario: +{amount} besitos",
}
```

---

## 4. Pasos Concretos de Preparación

### Fase 1: Preparación de Base de Datos

1. **Crear migración para renombrar `points` a `besitos`** en GamificationProfile
2. **Agregar campos nuevos** a GamificationProfile (story_progress, clues_collected, badges, inventory)
3. **Crear modelos nuevos**: ShopProduct, ShopTransaction, StoryChapter, Clue, Badge
4. **Actualizar BotConfig** con configuración de narrativa
5. **Crear script de seed** para datos iniciales de productos, pistas, capítulos

### Fase 2: Extensión del EventBus

1. **Agregar nuevos eventos** a la clase Events
2. **Documentar payload** esperado para cada evento nuevo
3. **Crear tests** para verificar que los eventos se emiten correctamente

### Fase 3: Crear Servicio de Narrativa

1. **Crear `/bot/services/narrative_service.py`**:
   - Métodos para gestionar progreso de historia
   - Métodos para combinar pistas
   - Métodos para desbloquear capítulos
   - Métodos para otorgar insignias

2. **Crear `/bot/services/shop_service.py`**:
   - `get_products()`: Listar productos disponibles
   - `purchase_product(user_id, product_id)`: Comprar producto
   - `get_user_inventory(user_id)`: Ver inventario
   - `use_product(user_id, product_id)`: Usar producto

3. **Registrar servicios nuevos** en ServiceContainer

### Fase 4: Extender GamificationService

1. **Renombrar método `add_points`** a `add_besitos` (mantener alias para compatibilidad)
2. **Agregar método `spend_besitos`** con validación de balance
3. **Extender `claim_daily_reward`** para incluir regalo de besitos
4. **Agregar listener** para evento `REACTION_ADDED` que otorgue besitos adicionales

### Fase 5: Crear Handlers de Usuario

1. **Crear `/bot/handlers/narrative.py`**:
   - `/historia`: Ver progreso narrativo
   - `/pistas`: Ver pistas coleccionadas
   - `/combinar`: Combinar pistas

2. **Crear `/bot/handlers/shop.py`**:
   - `/tienda`: Ver productos disponibles
   - `/comprar [id]`: Comprar producto
   - `/inventario`: Ver inventario
   - `/usar [id]`: Usar producto

3. **Extender `/bot/handlers/user.py`**:
   - `/besitos`: Ver balance de besitos
   - `/insignias`: Ver insignias obtenidas

### Fase 6: Crear Handlers de Admin

1. **Extender `/bot/handlers/admin.py`** con menú de narrativa:
   - Gestionar Productos
   - Gestionar Capítulos
   - Gestionar Pistas
   - Gestionar Insignias
   - Ver estadísticas de narrativa

### Fase 7: Integración con Sistema Existente

1. **Conectar reacciones con besitos**: Modificar listener de `REACTION_ADDED` para otorgar besitos
2. **Conectar subida de rango con narrativa**: Listener en `LEVEL_UP` para desbloquear contenido
3. **Conectar compras con desbloqueos**: Productos pueden desbloquear capítulos o pistas

### Fase 8: UI y Experiencia de Usuario

1. **Crear menús inline** para tienda con paginación
2. **Crear visualizador de historia** con capítulos desbloqueados
3. **Crear interfaz de combinación de pistas** interactiva
4. **Agregar notificaciones** para cada acción narrativa

---

## 5. Consideraciones Arquitectónicas

### 5.1 Mantenibilidad
- **Mantener separación de servicios**: NarrativeService y ShopService deben ser independientes
- **Usar EventBus para comunicación**: No crear dependencias directas entre módulos
- **Seguir patrones existentes**: Handlers separados, estados FSM organizados

### 5.2 Escalabilidad
- **Usar JSON para datos variables**: inventory, story_progress, clues permiten extensión sin migraciones
- **Índices en base de datos**: Agregar índices para user_id en nuevas tablas
- **Cachear configuración**: Extender patrón de cache de ConfigService

### 5.3 Seguridad
- **Validar transacciones**: Verificar balance antes de compras
- **Prevenir duplicados**: Evitar doble otorgamiento de recompensas
- **Logging**: Registrar todas las transacciones de tienda

### 5.4 Compatibilidad
- **Migración gradual**: Los usuarios existentes deben mantener sus puntos como besitos
- **Feature flags**: Usar `narrative_enabled` y `shop_enabled` para activación gradual
- **Backwards compatibility**: Mantener endpoints existentes funcionando

---

## 6. Diagrama de Integración

```
[Usuario Reacciona a Post]
        │
        v
[EventBus: REACTION_ADDED]
        │
        ├──> [GamificationService: +10 puntos]
        │
        └──> [NarrativeService: +5 besitos] <── NUEVO
        │
        v
[Verificar Umbrales]
        │
        ├──> [Si nuevo rango: LEVEL_UP event]
        │            │
        │            ├──> [Desbloquear capítulo?]
        │            └──> [Entregar recompensa?]
        │
        └──> [Si suficientes besitos: Notificar tienda]

[Usuario Compra Producto]
        │
        v
[ShopService.purchase_product]
        │
        ├──> [Validar balance besitos]
        ├──> [Deducir besitos]
        ├──> [Agregar a inventario]
        └──> [EventBus: PRODUCT_PURCHASED]
                    │
                    └──> [NarrativeService: Verificar desbloqueos]

[Usuario Combina Pistas]
        │
        v
[NarrativeService.combine_clues]
        │
        ├──> [Validar pistas en inventario]
        ├──> [Verificar combinación válida]
        ├──> [Generar resultado: badge/chapter/vip]
        └──> [EventBus: CLUE_COMBINED]
                    │
                    ├──> [Posible BADGE_EARNED]
                    └──> [Posible CHAPTER_UNLOCKED]
```

---

## 7. Archivos Críticos para la Implementación

| Archivo | Razón |
|---------|-------|
| `bot/database/models.py` | Modelos de BD que necesitan extensión con nuevas tablas y campos |
| `bot/services/gamification_service.py` | Servicio central que debe extenderse para manejar besitos |
| `bot/services/event_bus.py` | EventBus que necesita nuevos eventos para el sistema narrativo |
| `bot/services/dependency_injection.py` | ServiceContainer donde se registrarán los nuevos servicios |
| `bot/services/notification_service.py` | Plantillas de notificación que necesitan extensión |

---

## 8. Resumen Ejecutivo

### El sistema ESTÁ preparado para:
- Agregar nuevos servicios (arquitectura extensible)
- Comunicación entre módulos (EventBus funcional)
- Flujos interactivos complejos (WizardService disponible)

### El sistema NECESITA preparación en:
1. **Renombrar puntos a besitos** (cambio conceptual fundamental)
2. **Extender modelos de BD** (nuevos campos y tablas)
3. **Agregar eventos al EventBus** (comunicación narrativa)
4. **Crear servicios nuevos** (NarrativeService, ShopService)
5. **Extender configuración global** (feature flags, valores por defecto)

### Recomendación:
Ejecutar las Fases 1-2 primero (base de datos y eventos) antes de implementar funcionalidad, para asegurar una base sólida sobre la cual construir el módulo narrativo.
