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

### 3. Capa de Persistencia (Database)

En `bot/database/` se encuentra la capa de persistencia:

- **models.py**: Definición de modelos ORM
- **base.py**: Configuración base de SQLAlchemy

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

### Middleware
Implementado para:
- Autenticación de administradores
- Inyección de sesiones de base de datos

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

## Mejoras de Código

### Seguridad de Tipos
- Anotaciones de tipo completas en todos los servicios y handlers
- Uso de TypedDict para estructuras de retorno
- Validación de tipos en tiempo de ejecución

### Manejo de Errores
- Implementación de jerarquía de excepciones personalizadas
- Manejo específico de errores de base de datos y API de Telegram
- Mejora en la retroalimentación de errores al usuario

### Estructura de Importación
- Organización de importaciones siguiendo estilo PEP 8
- Agrupación lógica de dependencias estándar, terceros y locales

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

## Seguridad

- Middleware de autenticación para verificar roles de administrador
- Validación de tokens de suscripción
- Protección contra uso múltiple de tokens