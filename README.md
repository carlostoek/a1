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
- [Historial de Cambios](docs/CHANGELOG.md) - Registro de versiones y cambios

## Contribución

1. Hacer fork del proyecto
2. Crear una rama (`git checkout -b feature/nueva-funcionalidad`)
3. Hacer commit de los cambios (`git commit -m 'Añadir nueva funcionalidad'`)
4. Hacer push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abrir un Pull Request

## Licencia

[MIT](LICENSE)