# Estructura de Menús del Bot

## Menú Principal de Administración

### Opciones Disponibles
- **💎 Gestión VIP** (`admin_vip`)
- **🆓 Gestión Free** (`admin_free`)
- **⚙️ Configuración** (`admin_config`)
- **📊 Estadísticas** (`admin_stats`)

## Menú VIP

### Opciones Disponibles
- **🎟️ Generar Token ([Nombre Tarifa])** (`token_generate_{id}`) - Genera tokens VIP para cada tarifa configurada
- **📢 Enviar Publicación** (`admin_send_channel_post`) - Envía publicaciones al canal VIP
- **👥 Gestionar Suscriptores** (`vip_manage`) - Gestión de suscriptores VIP activos
- **📊 Ver Stats** (`vip_stats`) - Estadísticas de suscriptores VIP
- **💰 Configurar Tarifas** (`config_tiers`) - Gestión de tarifas de suscripción
- **💋 Configurar Reacciones** (`vip_config_reactions`) - Configuración de reacciones inline
- **⚙️ Configurar** (`vip_config`) - Submenú de configuración adicional del canal VIP

### Submenú de Configuración VIP
- **📊 Ver Stats** (`vip_stats`) - Estadísticas de suscriptores VIP
- **💄 Configurar Reacciones** (`vip_config_reactions`) - Configuración de reacciones inline

## Menú Free

### Opciones Disponibles
- **📢 Enviar Publicación** (`send_to_free_channel`) - Envía publicaciones al canal gratuito
- **📊 Ver Stats** (`free_stats`) - Estadísticas del canal gratuito
- **⚡ Procesar Pendientes** (`process_pending_now`) - Procesamiento masivo de solicitudes pendientes
- **⏱️ Configurar Tiempo de Espera** (`free_wait_time_config`) - Configuración del tiempo de espera
- **💋 Configurar Reacciones** (`free_config_reactions`) - Configuración de reacciones inline
- **⚙️ Configurar** (`free_config`) - Submenú de configuración del canal gratuito

### Submenú de Configuración Free
- **📊 Ver Stats** (`free_stats`) - Estadísticas del canal gratuito
- **💄 Configurar Reacciones** (`free_config_reactions`) - Configuración de reacciones inline
- **⏱️ Configurar Tiempo de Espera** (`free_wait_time_config`) - Configuración del tiempo de espera

## Menú de Configuración

### Opciones Disponibles
- **💰 Gestionar Tarifas** (`config_tiers`) - Gestión de tarifas de suscripción VIP
- **📡 Configurar Canales** (`config_channels_menu`) - Configuración de IDs de canales
- **Volver** (`admin_main_menu`) - Regresa al menú principal

### Submenú de Configuración de Canales
- **Canal VIP** (`setup_vip_select`) - Configuración del canal VIP
- **Canal Free** (`setup_free_select`) - Configuración del canal gratuito
- **Volver** (`admin_config`) - Regresa al menú de configuración

## Menú de Estadísticas

### Opciones Disponibles
- **📊 General** (`stats_general`) - Estadísticas generales del bot
- **💎 VIP** (`stats_vip`) - Estadísticas de suscripciones VIP
- **💬 FREE** (`stats_free`) - Estadísticas del canal gratuito
- **Volver** (`admin_main_menu`) - Regresa al menú principal

### Submenús de Estadísticas

#### Estadísticas Generales
- **Total de Usuarios Únicos** - Conteo de usuarios registrados
- **Suscripciones VIP Activas** - Usuarios con suscripción VIP activa
- **Suscripciones VIP Históricas** - Usuarios con suscripciones expiradas o revocadas
- **Tokens de Invitación Generados** - Conteo de tokens generados
- **Ingresos Totales Estimados** - Placeholder para futura implementación

#### Estadísticas VIP
- **Distribución por Tarifa** - Conteo de usuarios activos por tarifa
- **Tokens Redimidos** - Tokens de invitación utilizados
- **Tokens Expirados/Sin Usar** - Tokens no utilizados o expirados

#### Estadísticas Free
- **Solicitudes Pendientes** - Solicitudes de acceso en espera
- **Solicitudes Procesadas** - Historial de solicitudes aprobadas
- **Solicitudes Rechazadas/Limpiadas** - Solicitudes rechazadas o eliminadas

## Submenús de Configuración

### Submenú de Configuración VIP (`vip_config`)
- **📊 Ver Stats** (`vip_stats`) - Estadísticas de suscriptores VIP
- **💄 Configurar Reacciones** (`vip_config_reactions`) - Configuración de reacciones inline

### Submenú de Configuración Free (`free_config`)
- **📊 Ver Stats** (`free_stats`) - Estadísticas del canal gratuito
- **💄 Configurar Reacciones** (`free_config_reactions`) - Configuración de reacciones inline
- **⏱️ Configurar Tiempo de Espera** (`free_wait_time_config`) - Configuración del tiempo de espera

## Navegación entre Menús

### Botones de Navegación Estandarizados
- **⬅️ Volver** - Regresa al menú anterior
- **🏠 Principal** - Regresa al menú principal de administración
- **✅ Sí / ❌ No** - Confirmación de decisiones (por ejemplo, incluir reacciones)
- **🚀 Enviar / ❌ Cancelar** - Confirmación final de envío de publicaciones

### Flujos de Configuración con FSM
- **Creación/Edición de Tarifas** - Proceso de 3 pasos para definir nombre, duración y precio
- **Configuración de Tiempo de Espera** - Ingreso de valor numérico en minutos
- **Configuración de Reacciones** - Ingreso de emojis separados por coma
- **Configuración de Canales** - Ingreso de ID numérico o reenvío de mensaje del canal

## Gestión de Suscriptores VIP

### Funcionalidades Disponibles
- **Visualización Paginada** - Lista de suscriptores activos (5 por página)
- **Detalles del Usuario** - Información completa de cada suscriptor
- **Revocación de Acceso** - Expulsión del canal y actualización de estado
- **Navegación entre Páginas** - Controles de paginación con anterior/siguiente

## Procesamiento de Solicitudes Pendientes

### Funcionalidad Masiva
- **Procesamiento Automático** - Aprobación de todas las solicitudes pendientes
- **Envío de Enlaces Individuales** - Enlaces de invitación únicos por usuario
- **Actualización de Estados** - Marcado de solicitudes como procesadas
- **Reporte de Resultados** - Informe de solicitudes procesadas y errores