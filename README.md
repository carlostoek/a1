# Bot de Administración de Telegram

Un bot de Telegram multifuncional para la gestión de suscripciones VIP y acceso gratuito a canales, con panel de administración completo y sistema de tokens.

## Características

- **Sistema de Suscripción VIP**: Configuración de diferentes tarifas con duración y precios
- **Tokens de Invitación**: Generación y canje de tokens para acceso VIP
- **Acceso Gratuito**: Sistema de colas con tiempos de espera configurables
- **Panel de Administración**: Interfaz completa para gestión de usuarios y canales
- **Configuración Flexible**: Personalización de tiempos, reacciones y canales
- **Publicación de Contenido**: Envío de posts con reacciones opcionales a canales VIP y Free
- **Estadísticas**: Seguimiento de usuarios activos y solicitudes pendientes
- **Mejoras de PR12**:
  - Flujo de envío de posts con mejor manejo de errores
  - Consolidación de código duplicado
  - Seguridad de tipos con anotaciones apropiadas
  - Manejo de excepciones mejorado
  - Método compartido para obtener reacciones
  - Importaciones organizadas según PEP 8
  - Validación de tipo de canal para prevenir publicación incorrecta

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