# Servicio de Estadísticas (StatsService)

## Descripción General

El `StatsService` es un servicio dedicado para la recuperación y agregación de estadísticas del bot de Telegram. Proporciona vistas detalladas sobre el estado general del bot, las suscripciones VIP y las solicitudes del canal gratuito.

## Funcionalidades

### 1. Estadísticas Generales
- **Método**: `get_general_stats(session)`
- **Descripción**: Obtiene estadísticas generales del bot
- **Datos incluidos**:
  - Total de usuarios únicos registrados
  - Suscripciones VIP activas
  - Suscripciones VIP históricas (expiradas/revocadas)
  - Tokens de invitación generados
  - Ingresos totales estimados (placeholder)

### 2. Estadísticas VIP
- **Método**: `get_vip_stats(session)`
- **Descripción**: Obtiene estadísticas específicas de suscripciones VIP
- **Datos incluidos**:
  - Distribución por tarifa (cantidad de usuarios por tarifa de suscripción)
  - Tokens de invitación redimidos
  - Tokens expirados/sin usar

### 3. Estadísticas del Canal Gratuito
- **Método**: `get_free_channel_stats(session)`
- **Descripción**: Obtiene estadísticas del canal gratuito
- **Datos incluidos**:
  - Solicitudes pendientes
  - Solicitudes procesadas (histórico)
  - Solicitudes rechazadas/limpiadas

## Flujos de Interacción

### Dashboard de Estadísticas
1. **Acceso**: Admin → Stats (desde menú principal)
2. **Selección**: Elegir tipo de estadísticas (General, VIP, Free)
3. **Visualización**: Ver estadísticas específicas según selección

### Flujos de Datos
- Cada método del servicio ejecuta consultas SQL específicas
- Los resultados se formatean en diccionarios estructurados
- Las estadísticas se presentan en formato legible para el administrador

## Implementación Técnica

### Consultas SQL
- Utiliza SQLAlchemy ORM para consultas seguras
- Ejecuta operaciones de agregación (COUNT, GROUP BY)
- Maneja relaciones entre modelos (UserSubscription, InvitationToken, FreeChannelRequest)

### Manejo de Errores
- Cada método incluye manejo de excepciones
- Devuelve mensajes de error descriptivos
- Asegura la integridad de las operaciones de base de datos

## Integración con Handlers

### Admin Handler
- `admin_stats_menu()`: Presenta el menú principal de estadísticas
- `view_general_stats()`: Muestra estadísticas generales
- `view_vip_stats()`: Muestra estadísticas VIP
- `view_free_stats()`: Muestra estadísticas del canal gratuito

## Seguridad
- Acceso restringido a usuarios administradores
- Validación de permisos antes de mostrar estadísticas
- Consultas SQL parametrizadas para prevenir inyección

## Consideraciones de Rendimiento
- Consultas optimizadas con índices apropiados
- Uso eficiente de sesiones de base de datos
- Formateo de resultados en memoria para rápida visualización