# Comandos del Bot

## Comandos Públicos

### `/start [token]`

**Descripción**: Comando principal para interactuar con el bot. Puede usarse para:
- Iniciar una conversación con el bot
- Canjear un token de suscripción VIP

**Flujo**:
1. Si no se proporciona token: Muestra mensaje de bienvenida
2. Si se proporciona token: Intenta canjear el token VIP
   - Si es válido: Activa la suscripción VIP y envía enlace al canal VIP
   - Si es inválido: Muestra mensaje de error

**Ejemplo de uso**:
```
/start
/start a1b2c3d4-e5f6-7890-1234-567890abcdef
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

#### Ver Stats
- **Descripción**: Muestra estadísticas de suscriptores VIP
- **Salida**: Número de usuarios VIP activos

#### Configurar
- **Descripción**: Accede a las opciones de configuración VIP
- **Opciones disponibles**:
  - Ver estadísticas
  - Configurar reacciones inline

### Gestión Free

#### Ver Stats
- **Descripción**: Muestra estadísticas del canal gratuito
- **Salida**: 
  - Solicitudes totales
  - Solicitudes pendientes

#### Configurar
- **Descripción**: Accede a las opciones de configuración del canal gratuito
- **Opciones disponibles**:
  - Ver estadísticas
  - Configurar reacciones inline
  - Configurar tiempo de espera

### Configuración

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