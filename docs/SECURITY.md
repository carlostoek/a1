# Guía de Seguridad

## Visión General

El bot de administración de Telegram implementa múltiples capas de seguridad para proteger tanto a los usuarios como al sistema administrativo. Esta guía detalla las medidas de seguridad implementadas y las mejores prácticas recomendadas.

## Autenticación y Autorización

### Middleware de Autenticación de Administradores

El bot utiliza un middleware de autenticación (`AdminAuthMiddleware`) que protege todos los handlers de administración:

```python
admin_router.callback_query.middleware(AdminAuthMiddleware())
```

**Funcionalidad**:
- Verifica que el usuario que realiza la acción esté en la lista de administradores
- Rechaza solicitudes de usuarios no autorizados

**Fuente**: `bot/middlewares/auth.py`

### Lista de Administradores

La lista de IDs de administradores se configura en la variable de entorno `ADMIN_IDS`:

- Puede ser un array JSON: `[123456789, 987654321]`
- O una lista separada por comas: `123456789,987654321`
- Se valida en tiempo de ejecución por la clase `Settings`

## Validación de Entrada

### Validación de Tokens

- **Formato**: Verificación de formato UUID o alfanumérico con al menos 6 caracteres
- **Longitud mínima**: 6 caracteres
- **Tipos admitidos**: UUID estándar o cadena alfanumérica
- **Patrones regex**: 
  - UUID: `^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$`
  - Alfanumérico: `^[a-zA-Z0-9_-]+$`

### Validación de IDs de Canal

- **Verificación de formato**: Acepta solo IDs numéricos válidos
- **Verificación de existencia**: Confirma que el bot sea administrador del canal objetivo
- **Manejo de errores**: Proporciona mensajes claros para entradas inválidas

### Validación de Estados FSM

- Cada estado FSM incluye validación de entrada específica
- Limpieza de estado automática en caso de errores
- Verificación de permisos de administrador en cada paso

## Seguridad en Base de Datos

### Protección contra Inyección SQL

- Uso de SQLAlchemy ORM con consultas parametrizadas
- Validación de entradas antes de operaciones de base de datos
- Manejo seguro de sesiones con middleware

### Integridad de Datos

- Restricciones únicas en campos críticos (`user_id`, `token`, `name`)
- Validaciones en el nivel de modelo
- Transacciones con rollback en caso de error

## Seguridad en la API de Telegram

### Validación de Enlaces de Invitación

- **Uso único**: Enlaces de invitación generados con `member_limit=1`
- **Expiración temporal**: Enlaces que expiran cuando finaliza la suscripción
- **Generación segura**: Solo para usuarios que han canjeado tokens válidos

### Protección contra Abuso

- **Sistema de colas**: Acceso gratuito con tiempo de espera configurable
- **Límites de solicitudes**: Prevención de spam a través de colas
- **Control de estados**: Verificación de suscripciones activas antes de otorgar acceso

## Gestión de Tokens

### Generación de Tokens

- **UUID único**: Cada token generado es un UUID v4 único
- **Vinculación a tarifas**: Tokens vinculados a tarifas de suscripción específicas
- **Control de uso**: Marca de uso para prevenir uso múltiple

### Canje de Tokens

- **Verificación de uso previo**: Chequeo de tokens ya utilizados
- **Validación de formato**: Confirmación del formato del token
- **Expiración**: Tokens pueden expirar según la lógica de negocio

## Configuración Segura

### Variables de Entorno

- **Token de Bot**: Guardado como variable de entorno, no en código
- **IDs de Administrador**: No expuestos en código fuente
- **URL de Base de Datos**: Configurable, con valor por defecto seguro

### Configuración en Tiempo de Ejecución

- **Caché de Configuración**: La configuración se almacena en memoria con control de concurrencia
- **Actualización segura**: Cambios a configuración validados y registrados

## Manejo de Errores Seguro

### Información de Error

- **Mensajes controlados**: No revelan información sensible del sistema
- **Registro de errores**: Errores críticos registrados para monitoreo
- **Respuestas amigables**: Mensajes de error comprensibles para usuarios

### Prevención de Errores de Exposición

- **Manejo de excepciones**: Captura y manejo específico de excepciones
- **Validación de entradas**: Verificación antes de procesar datos
- **Escapado de salidas**: Protección contra XSS en mensajes HTML

## Seguridad en Canales

### Verificación de Acceso

- **Verificación de administrador**: Confirma que el bot tiene permisos antes de guardar ID de canal
- **Acceso controlado**: Solo administradores pueden configurar canales
- **Identificación segura**: Validación de IDs numéricos o reenvío de mensajes

### Protección de Canales

- **Enlaces temporales**: Acceso a canales VIP a través de enlaces con expiración
- **Control de membresía**: Verificación de suscripción activa antes de otorgar acceso

## Monitoreo y Auditoría

### Registro de Actividades

- **Generación de tokens**: Registro de quién generó tokens y cuándo
- **Uso de tokens**: Seguimiento de tokens canjeados y por quién
- **Acciones de administrador**: Registro de configuraciones y cambios

### Estadísticas de Seguridad

- **Solicitudes fraudulentas**: Detección de intentos de acceso no autorizado
- **Patrones de uso**: Identificación de posibles abusos del sistema

## Mejores Prácticas Recomendadas

### Para Administradores

1. **Mantener actualizada la lista de administradores**
2. **Revisar regularmente la generación y uso de tokens**
3. **Monitorear el acceso a canales**
4. **Mantener seguros los tokens de bot**

### Para Desarrolladores

1. **Validar todas las entradas de usuario**
2. **Implementar manejo seguro de errores**
3. **Mantener actualizadas las dependencias**
4. **Realizar revisiones de seguridad regulares**

### Para Despliegue

1. **Usar entornos aislados**
2. **Aplicar políticas de firewall adecuadas**
3. **Realizar copias de seguridad regulares**
4. **Monitorear el sistema en producción**

## Actualizaciones de Seguridad

- **Monitoreo de dependencias**: Revisar regularmente por vulnerabilidades
- **Actualización de bibliotecas**: Mantener Aiogram, SQLAlchemy y otras bibliotecas actualizadas
- **Revisión de código**: Auditar regularmente el código en busca de posibles vulnerabilidades