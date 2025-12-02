# Gestión de Suscriptores VIP

## Descripción General

El sistema de gestión de suscriptores VIP permite a los administradores visualizar, administrar y revocar el acceso VIP de usuarios activos. Incluye funcionalidades de paginación para manejar grandes listas de suscriptores de manera eficiente.

## Características Principales

- **Visualización Paginada**: Lista de suscriptores VIP activos con paginación (5 usuarios por página)
- **Información Detallada**: Vista detallada de cada suscriptor con ID, fechas de registro y expiración
- **Revocación de Acceso**: Funcionalidad para revocar el acceso VIP y expulsar al usuario del canal VIP
- **Navegación Intuitiva**: Controles de paginación y navegación entre vistas
- **Eficiencia de Memoria**: Sistema optimizado para manejar grandes volúmenes de suscriptores sin sobrecarga de memoria

## Arquitectura del Sistema

### Componentes Principales

1. **Handlers (admin.py)**:
   - `view_subscribers_list_first_page()`: Muestra la primera página de suscriptores
   - `view_subscribers_list_page()`: Muestra una página específica de suscriptores
   - `view_subscriber_detail()`: Muestra información detallada de un suscriptor
   - `process_revocation()`: Procesa la revocación de acceso VIP

2. **Servicios (subscription_service.py)**:
   - `get_active_vips_paginated()`: Obtiene lista paginada de suscriptores VIP
   - `revoke_vip_access()`: Revoca acceso VIP y expulsa del canal

3. **Utilidades (ui.py)**:
   - `create_pagination_keyboard()`: Crea controles de paginación

4. **Modelos (models.py)**:
   - `UserSubscription`: Modelo de datos para suscriptores

## Flujos de Trabajo

### Visualización de Suscriptores

1. El administrador selecciona "Gestionar Suscriptores" en el menú VIP
2. El sistema llama a `view_subscribers_list_first_page()` que invoca `view_subscribers_list()` con `page=1`
3. Se calcula el número total de páginas basado en el tamaño de página (5)
4. Se muestra la primera página con:
   - Título: "GESTIÓN DE SUSCRIPTORES VIP"
   - Total de suscriptores activos
   - Lista de suscriptores con ID, fecha de expiración y fecha de registro
   - Botones para ver detalles de cada usuario
   - Controles de paginación (anterior/siguiente)
   - Botón de "Volver" al menú VIP

### Navegación de Paginación

1. El administrador presiona "➡️" o "⬅️" para navegar entre páginas
2. El callback `view_subscribers_list_page()` extrae el número de página del callback data
3. Se vuelve a llamar a `view_subscribers_list()` con el número de página correspondiente
4. El sistema actualiza el mensaje con la nueva página de suscriptores

### Vista Detallada de Suscriptor

1. El administrador presiona el botón de un suscriptor específico
2. El callback `view_subscriber_detail()` extrae el ID del usuario del callback data
3. Se consulta la base de datos para obtener detalles del suscriptor
4. Se muestra información detallada:
   - ID del usuario
   - Fecha de registro
   - Fecha de expiración
   - Días restantes
   - Token usado (si aplica)
5. Opciones: "REVOCAR ACCESO" o "Volver a Lista"

### Revocación de Acceso VIP

1. El administrador selecciona "REVOCAR ACCESO" en la vista detallada
2. El callback `process_revocation()` extrae el ID del usuario del callback data
3. Se llama a `SubscriptionService.revoke_vip_access()` que:
   - Verifica que el usuario tenga una suscripción VIP activa
   - Expulsa al usuario del canal VIP usando `bot.ban_chat_member()`
   - Actualiza el estado de la suscripción a "revoked" y el rol a "free"
   - Guarda los cambios en la base de datos
4. El sistema notifica el resultado y regresa a la lista de suscriptores

## Implementación Técnica

### Paginación Eficiente

```python
PAGE_SIZE = 5
users, total_count = await SubscriptionService.get_active_vips_paginated(page, PAGE_SIZE, session)
total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE if total_count > 0 else 1
```

- El tamaño de página es fijo en 5 usuarios para mantener la legibilidad
- Se calcula el número total de páginas basado en el conteo total
- Se utilizan operaciones `OFFSET` y `LIMIT` en la base de datos para eficiencia

### Consultas de Base de Datos

La función `get_active_vips_paginated()` ejecuta dos consultas separadas:
1. Una para contar el total de suscriptores VIP activos
2. Otra para obtener solo los registros de la página actual

Esto permite una paginación precisa y eficiente sin cargar todos los registros en memoria.

### Controles de Paginación

Los controles de paginación se generan dinámicamente usando `MenuFactory.create_pagination_keyboard()`:
- Botón "⬅️" para página anterior (solo si no es la primera página)
- Botón con información de página actual/total
- Botón "➡️" para página siguiente (solo si no es la última página)

### Revocación Segura

La revocación de acceso VIP incluye múltiples pasos de seguridad:
1. Validación de que el usuario tenga una suscripción VIP activa
2. Expulsión del canal VIP (con manejo de errores para casos donde el usuario ya está expulsado)
3. Actualización del estado en la base de datos
4. Confirmación de la operación

## Callback Data Patterns

- `vip_manage`: Iniciar visualización de la primera página
- `vip_page_{page_number}`: Navegar a una página específica
- `vip_user_detail_{user_id}`: Ver detalles de un suscriptor específico
- `vip_revoke_confirm_{user_id}`: Confirmar revocación de acceso para un usuario

## Errores y Excepciones

- **ID de usuario inválido**: Manejado con validación de `int()` y mensajes de error claros
- **Usuario no encontrado**: Verificado antes de mostrar detalles
- **Error de base de datos**: Capturado y manejado con rollback de transacción
- **Error de API de Telegram**: Manejado para casos donde el bot no puede expulsar al usuario

## Consideraciones de Seguridad

- Solo administradores pueden acceder a las funciones de gestión de suscriptores
- Validación de roles y permisos a través de `AdminAuthMiddleware`
- Protección contra acceso no autorizado a detalles de suscriptores

## Rendimiento y Escalabilidad

- El sistema de paginación permite manejar grandes volúmenes de suscriptores
- Uso eficiente de consultas SQL con `OFFSET` y `LIMIT`
- Carga selectiva de solo los registros necesarios para cada página
- Optimización de memoria al no cargar todos los suscriptores a la vez