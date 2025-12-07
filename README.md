# Bot de Administración de Telegram

Un bot de Telegram multifuncional para la gestión de suscripciones VIP y acceso gratuito a canales, con panel de administración completo y sistema de tokens.

## Características

- **Sistema de Suscripción VIP**: Configuración de diferentes tarifas con duración y precios
- **Tokens de Invitación**: Generación y canje de tokens para acceso VIP
- **Acceso Gratuito**: Sistema de colas con tiempos de espera configurables
- **Panel de Administración**: Interfaz completa para gestión de usuarios y canales
- **Configuración Flexible**: Personalización de tiempos, reacciones y canales
- **Publicación de Contenido**: Envío de posts con reacciones opcionales a canales VIP y Free
- **Protección de Contenido**: Activación/desactivación de protección de contenido para canales VIP y Free
- **Inyección de Dependencias**: Patrón ServiceContainer para acceso centralizado a servicios
- **Servicio de Notificaciones**: Sistema de mensajería basado en plantillas para usuarios
- **Patrón Event Bus**: Sistema de eventos asíncrono para desacoplar módulos y permitir comunicación entre componentes
- **Estadísticas**: Seguimiento de usuarios activos y solicitudes pendientes
- **Sistema de Gamificación**: Sistema de puntos y rangos con recompensas para aumentar la participación de usuarios
- **Perfiles de Gamificación**: Almacenamiento de puntos, rangos y actividad de usuarios
- **Sistema de Recompensas Avanzado**: Rangos incluyen recompensas concretas como días de suscripción VIP y packs de contenido exclusivos
- **RewardContentPack y RewardContentFile**: Modelos para gestionar packs de contenido multimedia como recompensas
- **GamificationService**: Servicio completo de gamificación que otorga puntos automáticamente por reacciones y notifica subidas de rango
- **Integración con Event Bus**: Sistema automatizado que otorga puntos cuando los usuarios reaccionan a publicaciones
- **Handler de Reacciones Inline**: Nuevo handler `process_inline_reaction` que procesa reacciones de usuarios y emite eventos al EventBus
- **Desacoplamiento UI-Negocio**: Implementación del patrón de separación entre capa de presentación y lógica de negocio a través del EventBus
- **Mejoras de PR12**:
  - Flujo de envío de posts con mejor manejo de errores
  - Consolidación de código duplicado
  - Seguridad de tipos con anotaciones apropiadas
  - Manejo de excepciones mejorado
  - Método compartido para obtener reacciones
  - Importaciones organizadas según PEP 8
  - Validación de tipo de canal para prevenir publicación incorrecta
- **Mejoras de PR23**:
  - **Nueva plantilla "rank_up"** en NotificationService para notificar subidas de rango
  - **Mejoras a GamificationService** con type hints, constantes y mejor manejo de errores
  - **Corrección de datetime.now** en GamificationProfile para usar timezone.utc
  - **Uso de SQLAlchemy ORM** en la función seed_ranks para inicializar rangos
  - **Eliminación de variables no utilizadas** en el código
  - **Mejora de eficiencia** en la consulta `_check_rank_up` con uso de `limit(1)`
  - **Implementación de constantes** como POINTS_PER_REACTION para valores fijos
  - **Mejoras de manejo de errores** con SQLAlchemyError y manejo específico de errores de Telegram
- **Mejoras de PR24**:
  - **Corrección de bug de `new_expiry`** en SubscriptionService para calcular correctamente la fecha de expiración al extender suscripciones
  - **Implementación de relaciones SQLAlchemy** descomentadas en modelos de base de datos para mejor integridad referencial
  - **Adición del handler `pack_view`** en admin handlers para visualizar detalles de packs de contenido
  - **Refactorización para evitar objetos mock** en la gestión de rangos para mejorar la claridad del código
  - **Implementación de eliminación en cascada ORM** en GamificationService para eliminar packs de contenido y sus archivos asociados
  - **Mejora del manejo de excepciones** con manejo específico de `TelegramAPIError` para errores de la API de Telegram
- **Sistema de Gestión de Packs de Contenido**: Nuevo sistema para crear y administrar packs de contenido multimedia como recompensas
  - **ContentPackCreationStates**: Estados FSM para el flujo de creación de packs de contenido
  - **Métodos GamificationService**: Funciones `create_content_pack`, `add_file_to_pack`, `get_all_content_packs`, `delete_content_pack`
  - **Soporte para múltiples tipos de medios**: Fotos, videos y documentos
  - **Integración con menú VIP**: Nueva opción "Packs de Recompensas" en el menú de administración VIP
  - **Infraestructura de contexto de retorno**: Sistema para mantener el contexto en flujos de creación anidados
- **Sistema de Gestión de Rangos y Recompensas**: Nuevo sistema integral para configurar recompensas asociadas a rangos de gamificación
  - **RankConfigStates**: Estados FSM para el flujo de configuración de recompensas de rangos
  - **Métodos GamificationService**: Funciones `get_all_ranks`, `update_rank_rewards`, `get_rank_by_id` para la gestión de rangos
  - **Integración con menú VIP**: Nueva opción "Rangos" en el menú de administración VIP
  - **Configuración de recompensas**: Posibilidad de asignar días VIP y packs de contenido a cada rango
  - **Flujo de creación anidada**: Sistema para crear packs de contenido directamente desde la configuración de rangos
  - **Flujo de edición de rangos**: Interfaz para modificar días VIP y asignar packs a rangos existentes
  - **Sistema de contexto de retorno**: Funcionalidad para mantener el contexto durante flujos anidados de creación y edición
- **Sistema de Entrega Automática de Recompensas**: Implementación completa del sistema que entrega recompensas configuradas cuando los usuarios suben de rango
  - **Entrega VIP**: Sistema automático que extiende la suscripción VIP de usuarios al subir de rango mediante el método `add_vip_days` del SubscriptionService
  - **Entrega de Pack de Contenido**: Sistema automático que envía archivos multimedia como álbum o archivos individuales cuando los usuarios suben de rango
  - **Método _deliver_rewards**: Función central en GamificationService que procesa y entrega recompensas configuradas
  - **Integración con _check_rank_up**: El método de verificación de subida de rango ahora llama a `_deliver_rewards` para entregar recompensas
  - **Nuevas plantillas de notificación**: "vip_reward" y "pack_reward" para notificar a usuarios sobre recompensas entregadas
  - **Clasificación de Medios**: Sistema inteligente que clasifica archivos multimedia para envío apropiado como álbum o archivos individuales
  - **Manejo de Errores**: Implementación de manejo específico para errores en envío de recompensas sin afectar el flujo principal de gamificación
- **Sistema de Recompensa Diaria**: Nuevo sistema de check-in diario que permite a los usuarios reclamar puntos gratis cada 24 horas
  - **Campo last_daily_claim**: Nuevo campo en GamificationProfile para rastrear la última reclamación diaria
  - **Template daily_success**: Notificación "📅 **¡Check-in Diario Completado!**\nHas ganado +{points} puntos por volver hoy.\n✅ Racha actual: {streak} días (Futuro)\n🏆 Total Puntos: {total_points}"
  - **Template daily_cooldown**: Notificación "⏳ **¡Vuelve más tarde!**\nYa reclamaste tu recompensa de hoy.\nPodrás reclamar de nuevo en: **{remaining_time}**."
  - **Método claim_daily_reward**: Implementación con lógica de cooldown de 24 horas y validación adecuada
  - **Recompensa fija**: 50 puntos por check-in diario
  - **Manejo de errores**: Validación y manejo de errores apropiado en el servicio de gamificación
  - **Handler /daily**: Nuevo comando para que los usuarios reclamen su recompensa diaria
- **Sistema de Referidos**: Sistema de referidos que permite a los usuarios invitar a amigos y ganar puntos
  - **Campo referred_by_id**: Nuevo campo en GamificationProfile que almacena el ID del usuario que lo invitó
  - **Campo referrals_count**: Nuevo campo en GamificationProfile que cuenta el número de referidos exitosos
  - **Método get_referral_link**: Genera un enlace de referido único para cada usuario
  - **Método process_referral**: Procesa las referencias cuando un nuevo usuario se une usando un enlace de referido
  - **Comando /invite**: Nuevo comando público que permite a los usuarios obtener su enlace de referido y ver estadísticas
  - **Integración con /start**: El comando /start ahora también maneja enlaces de referidos en adición a tokens VIP
  - **Mecánica de recompensas**: Referidor obtiene 100 puntos y referido obtiene 50 puntos al registrarse
  - **Protección contra fraude**: Sistema anti-bucle que previene auto-referidos y validaciones para evitar abusos

- **Wizard Engine**: Nuevo motor de wizards para crear flujos interactivos complejos con validación y lógica condicional
  - **Arquitectura en 3 capas**: Capa de presentación, capa de servicio y capa de core para máxima modularidad
  - **RankWizard**: Nuevo wizard para crear rangos de gamificación de manera guiada con validación de datos
  - **Validadores comunes**: Sistema de validación reutilizable para diferentes tipos de entrada
  - **UI Renderer**: Componentes para generar interfaces de usuario estándar como teclados Sí/No
  - **Gestión de estado**: Integración completa con FSM de Aiogram para persistencia de estado durante los wizards
  - **Integración con servicios**: Los wizards pueden acceder a servicios del bot para operaciones de negocio
  - **Flujos condicionales**: Soporte para lógica condicional basada en respuestas del usuario
  - **Handler genérico**: Manejadores de mensajes y callbacks que pueden trabajar con cualquier wizard implementado

## Instalación

1. **Clonar el repositorio**
   ```bash
   git clone <repositorio>
   cd a1
   ```

2. **Crear entorno virtual**
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno**
   ```bash
   cp .env.example .env
   # Editar .env y añadir tu token de bot y otros parámetros
   ```

## Configuración

Crear archivo `.env` con las siguientes variables:

```env
BOT_TOKEN=123456789:ABCdefGhIjKlMnOpQrStUvWxYz
ADMIN_IDS=[123456789, 987654321]
DB_URL=sqlite+aiosqlite:///bot.db
```

- `BOT_TOKEN`: Token obtenido de [@BotFather](https://t.me/BotFather)
- `ADMIN_IDS`: IDs de Telegram de administradores (formato JSON array o comma-separated)
- `DB_URL`: (Opcional) URL de conexión a base de datos (SQLite por defecto)

## Uso

1. **Iniciar el bot**
   ```bash
   python main.py
   ```

2. **Configurar el bot como administrador** en los canales VIP y gratuito

3. **Usar `/admin`** para acceder al panel de administración

4. **Configurar canales** y **tarifas de suscripción** desde el panel de administración

## Comandos

### Públicos
- `/start [token]` - Iniciar conversación o canjear token VIP
- `/free` - Solicitar acceso gratuito (con tiempo de espera)

### Administrador
- `/admin` - Acceder al panel de administración

## Documentación Adicional

- [Arquitectura](docs/ARCHITECTURE.md) - Estructura y diseño del sistema
- [Comandos](docs/COMMANDS.md) - Detalles de todos los comandos y flujos
- [API y Servicios](docs/API.md) - Interacciones y servicios del sistema
- [Modelos](docs/MODELS.md) - Estructura de base de datos
- [FSM](docs/FSM.md) - Máquinas de estados para flujos de configuración
- [Wizard Engine](docs/WIZARD_ENGINE.md) - Documentación del motor de wizards para flujos interactivos
- [Historial de Cambios](docs/CHANGELOG.md) - Registro de versiones y cambios

## Contribución

1. Hacer fork del proyecto
2. Crear una rama (`git checkout -b feature/nueva-funcionalidad`)
3. Hacer commit de los cambios (`git commit -m 'Añadir nueva funcionalidad'`)
4. Hacer push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abrir un Pull Request

## Licencia

[MIT](LICENSE)