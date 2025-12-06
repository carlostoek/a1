# Comandos del Bot

## Comandos Públicos

### `/start [token]`

**Descripción**: Comando principal para interactuar con el bot. Puede usarse para:
- Iniciar una conversación con el bot
- Canjear un token de suscripción VIP
- Iniciar el proceso de configuración inicial (onboarding) para administradores nuevos
- Procesar enlaces de referidos (formato `ref_...`)

**Flujo**:
1. Si se proporciona un payload de referido (`ref_...`): Procesa la referida independientemente del resto del flujo
2. Si se proporciona token: Intenta canjear el token VIP
   - Si es válido: Activa la suscripción VIP y envía enlace al canal VIP
   - Si es inválido: Muestra mensaje de error
3. Si es un administrador y es la primera vez que accede (no hay canales configurados): Inicia el flujo de onboarding
   - Presenta opciones de configuración rápida o completa
   - Guía al administrador a través del proceso de configuración inicial
4. Si no es administrador o ya está todo configurado: Muestra mensaje de bienvenida configurado

**Opciones de Onboarding**:
- **Configuración Rápida**: Configura canales y crea una tarifa básica
- **Configuración Completa**: Configura canales, protección de contenido, mensaje de bienvenida, puntos de gamificación y tarifa

**Ejemplo de uso**:
```
/start
/start a1b2c3d4-e5f6-7890-1234-567890abcdef
/start ref_12345
```

### `/free`

**Descripción**: Solicita acceso gratuito al canal gratuito.

**Flujo**:
1. Verifica si el usuario ya tiene una solicitud pendiente
2. Si no tiene solicitud pendiente: Registra la solicitud y notifica el tiempo de espera
3. Si ya tiene solicitud pendiente: Muestra tiempo restante

**Ejemplo de uso**:
```
/free
```

### `/daily`

**Descripción**: Reclama la recompensa diaria de puntos por check-in. Los usuarios pueden reclamar 50 puntos cada 24 horas.

**Flujo**:
1. Verifica si ha pasado al menos 24 horas desde la última reclamación
2. Si puede reclamar: Otorga 50 puntos y actualiza la fecha de última reclamación
3. Si aún está en cooldown: Muestra el tiempo restante hasta la próxima reclamación
4. Envía notificación personalizada según el resultado

**Ejemplo de uso**:
```
/daily
```

**Notificaciones**:
- **Éxito**: "📅 **¡Check-in Diario Completado!**\nHas ganado +{points} puntos por volver hoy.\n✅ Racha actual: {streak} días (Futuro)\n🏆 Total Puntos: {total_points}"
- **Cooldown**: "⏳ **¡Vuelve más tarde!**\nYa reclamaste tu recompensa de hoy.\nPodrás reclamar de nuevo en: **{remaining_time}**."

### `/invite`

**Descripción**: Genera un enlace de referido único para que el usuario invite a amigos y muestre estadísticas de referidos.

**Flujo**:
1. El bot genera un enlace único con el formato `https://t.me/nombre_bot?start=ref_user_id`
2. Muestra el enlace para que el usuario lo comparta
3. Muestra el número de referidos exitosos del usuario
4. Envía notificación con información sobre las recompensas por referidos

**Ejemplo de uso**:
```
/invite
```

**Notificación**:
```
🚀 ¡Gana Puntos Invitando!
Comparte este enlace con tus amigos. Cuando entren por primera vez, ambos ganan:
   Tú: +100 pts | Ellos: +50 pts

🔗 Tu Enlace: https://t.me/bot_username?start=ref_12345 (Toca para copiar)
👥 Has invitado a: 5 personas.
```

## Comandos de Administrador

### `/admin`

**Descripción**: Accede al panel de administración del bot.

**Requisitos**:
- El usuario debe estar en la lista de administradores (`ADMIN_IDS`)

**Funcionalidades disponibles**:
- Gestión VIP
- Gestión Free
- Configuración
- Estadísticas

## Funcionalidades del Panel de Administración

### Gestión VIP

#### Generar Token
- **Descripción**: Genera un token de suscripción VIP basado en una tarifa configurada
- **Requisitos**: Debe existir al menos una tarifa de suscripción activa
- **Salida**: Enlace de invitación con el token

#### Enviar Publicación
- **Descripción**: Envía una publicación al canal VIP con reacciones opcionales
- **Flujo**:
  1. Admin selecciona "Enviar Publicación" desde menú VIP
  2. Proporciona contenido (texto, foto, video, etc.)
  3. Si hay reacciones configuradas para VIP, se pregunta si incluir reacciones
  4. Se muestra previsualización exacta del formato final
  5. Admin confirma envío o cancela
- **Opciones**:
  - Si reacciones están configuradas: Seleccionar "Sí" o "No" para incluir reacciones
  - Confirmación final con botones "Enviar" o "Cancelar"
- **Mejoras de PR12**:
  - Validación robusta de tipo de canal para prevenir publicación incorrecta
  - Manejo mejorado de errores durante el proceso de envío
  - Uso del método compartido `get_reactions_for_channel` para obtener reacciones

#### Ver Stats
- **Descripción**: Muestra estadísticas de suscriptores VIP
- **Salida**: Número de usuarios VIP activos

#### Gestionar Suscriptores
- **Descripción**: Gestión completa de suscriptores VIP activos
- **Funcionalidades**:
  - Visualización paginada de suscriptores VIP
  - Información detallada por usuario
  - Revocación de acceso VIP y expulsión del canal
- **Flujo**:
  1. Visualización de lista paginada de suscriptores activos (5 por página)
  2. Cada suscriptor mostrado con ID, fecha de expiración y fecha de registro
  3. Botones para ver detalles de cada usuario
  4. Navegación entre páginas con controles de paginación
  5. Opción de revocar acceso desde la vista de detalles

#### Configurar Tarifas
- **Descripción**: Accede a la gestión de tarifas de suscripción VIP
- **Funcionalidades**:
  - Ver lista de tarifas existentes
  - Crear nueva tarifa
  - Editar tarifas existentes
  - Eliminar tarifas (desactivar)

#### Configurar Reacciones
- **Descripción**: Configura reacciones inline para el canal VIP
- **Flujo**:
  1. Admin selecciona "Configurar Reacciones" desde menú VIP
  2. Introduce emojis separados por coma (ej: 👍,🔥,🚀)
  3. Sistema guarda la lista de reacciones
  4. Las reacciones se aplican a las publicaciones futuras

#### Configurar
- **Descripción**: Accede al submenú de configuración VIP
- **Opciones disponibles**:
  - Ver estadísticas
  - Configurar reacciones inline

### Gestión Free

#### Enviar Publicación
- **Descripción**: Envía una publicación al canal gratuito con reacciones opcionales
- **Flujo**:
  1. Admin selecciona "Enviar Publicación" desde menú Free
  2. Proporciona contenido (texto, foto, video, etc.)
  3. Si hay reacciones configuradas para Free, se pregunta si incluir reacciones
  4. Se muestra previsualización exacta del formato final
  5. Admin confirma envío o cancela
- **Opciones**:
  - Si reacciones están configuradas: Seleccionar "Sí" o "No" para incluir reacciones
  - Confirmación final con botones "Enviar" o "Cancelar"
- **Mejoras de PR12**:
  - Validación robusta de tipo de canal para prevenir publicación incorrecta
  - Manejo mejorado de errores durante el proceso de envío
  - Uso del método compartido `get_reactions_for_channel` para obtener reacciones

#### Ver Stats
- **Descripción**: Muestra estadísticas del canal gratuito
- **Salida**:
  - Solicitudes totales
  - Solicitudes pendientes

#### Procesar Pendientes
- **Descripción**: Procesa manualmente todas las solicitudes pendientes de acceso gratuito
- **Flujo**:
  1. Admin selecciona "Procesar Pendientes" desde menú Free
  2. El sistema aprueba todas las solicitudes pendientes
  3. Se envían enlaces de invitación individuales a cada usuario
  4. Se actualiza el estado de las solicitudes como procesadas
- **Funcionalidad**: Aprobación masiva de solicitudes en espera

#### Configurar Tiempo de Espera
- **Descripción**: Configura el tiempo de espera para solicitudes de acceso gratuito
- **Flujo**:
  1. Admin selecciona "Configurar Tiempo de Espera" desde menú Free
  2. Introduce la duración en minutos (solo números enteros)
  3. Sistema actualiza la configuración
  4. El nuevo tiempo se aplica a nuevas solicitudes

#### Configurar Reacciones
- **Descripción**: Configura reacciones inline para el canal gratuito
- **Flujo**:
  1. Admin selecciona "Configurar Reacciones" desde menú Free
  2. Introduce emojis separados por coma (ej: 👍,🔥,🚀)
  3. Sistema guarda la lista de reacciones
  4. Las reacciones se aplican a las publicaciones futuras

#### Configurar
- **Descripción**: Accede al submenú de configuración del canal gratuito
- **Opciones disponibles**:
  - Ver estadísticas
  - Configurar reacciones inline
  - Configurar tiempo de espera

### Configuración

#### Vista de Estado General (Dashboard)
- **Descripción**: Vista general del estado de configuración del bot
- **Flujo**: Admin → Config → Vista de Estado General
- **Contenido del Dashboard**:
  - Estado de canales (VIP y Free): ✅ (configurado) o ❌ (pendiente)
  - Conteo de tarifas activas
  - Tiempo de espera configurado para canal gratuito
  - Estado de reacciones (VIP y Free): ✅ (configuradas) o ❌ (pendientes)
  - Formato de emojis indicando estado de cada componente
- **Salida**: Reporte formateado con emojis indicadores de estado

#### Gestionar Tarifas
- **Descripción**: Gestión de tarifas de suscripción VIP
- **Funcionalidades**:
  - Ver lista de tarifas existentes
  - Crear nueva tarifa
  - Editar tarifas existentes
  - Eliminar tarifas (desactivar)

#### Configurar Canales
- **Descripción**: Configuración de IDs de canales VIP y gratuito
- **Métodos de entrada**:
  - ID numérico directo (ej: -10012345678)
  - Reenvío de mensaje desde el canal objetivo

### Estadísticas Generales
- **Descripción**: Vista consolidada de estadísticas
- **Datos mostrados**:
  - Usuarios VIP activos
  - Solicitudes Free totales
  - Solicitudes pendientes

### Dashboard de Estadísticas
- **Descripción**: Nuevo dashboard de estadísticas con vistas detalladas
- **Flujo**: Admin → Stats → Elegir tipo de estadísticas → Ver estadísticas específicas
- **Opciones disponibles**:
  - **General**: Estadísticas generales del bot
    - Total de usuarios únicos
    - Suscripciones VIP activas
    - Suscripciones VIP históricas (expiradas/revocadas)
    - Tokens de invitación generados
    - Ingresos totales estimados (placeholder)
  - **VIP**: Estadísticas de suscripciones VIP
    - Distribución por tarifa (cantidad de usuarios por tarifa)
    - Tokens redimidos
    - Tokens expirados/sin usar
  - **Free**: Estadísticas del canal gratuito
    - Solicitudes pendientes
    - Solicitudes procesadas (histórico)
    - Solicitudes rechazadas/limpiadas

## Flujos FSM (Máquina de Estados Finitos)

### Creación/Edición de Tarifas
- **Estado inicial**: `waiting_tier_name`
- **Flujo**:
  1. `waiting_tier_name` → Introducir nombre
  2. `waiting_tier_duration` → Introducir duración en días
  3. `waiting_tier_price` → Introducir precio en USD
  4. Crear/editar tarifa en base de datos

### Configuración de Tiempo de Espera
- **Estado**: `WaitTimeSetupStates.waiting_wait_time_minutes`
- **Flujo**: Introducir número entero (minutos) → Actualizar configuración

### Configuración de Reacciones
- **Estado**: `ReactionSetupStates.waiting_reactions_input`
- **Flujo**: Introducir emojis separados por coma → Actualizar configuración

### Configuración de Canales
- **Estado**: `ChannelSetupStates.waiting_channel_id_or_forward`
- **Flujo**:
  - Opción 1: Enviar ID numérico del canal
  - Opción 2: Reenviar mensaje desde el canal objetivo

### Envío de Publicaciones
- **Estados**: `PostSendingStates`
  - `waiting_post_content`: Espera el contenido del post (texto, foto, video, etc.)
  - `waiting_reaction_decision`: Pregunta si incluir reacciones (si están configuradas)
  - `waiting_confirmation`: Muestra previsualización y espera confirmación
- **Flujo**:
  1. Admin selecciona enviar post a VIP o Free
  2. Proporciona contenido → `waiting_post_content`
  3. Si reacciones configuradas → `waiting_reaction_decision` (Sí/No)
  4. Previsualización exacta del formato final
  5. Confirmación final → `waiting_confirmation` (Enviar/Cancelar)
  6. Envío al canal correspondiente

### Procesamiento de Solicitudes Pendientes
- **Callback**: `process_pending_now`
- **Descripción**: Callback para procesar manualmente todas las solicitudes pendientes de acceso gratuito
- **Funcionalidad**: Aprobar todas las solicitudes pendientes de forma masiva y enviar enlaces de invitación individuales a los usuarios