# FSM (Máquina de Estados Finitos)

## Descripción General

El bot implementa Máquinas de Estados Finitos (FSM) para gestionar flujos de conversación complejos, principalmente para la configuración de parámetros y creación de elementos. Esta implementación permite mantener el contexto de la conversación con un usuario a lo largo de múltiples interacciones.

## Estados Disponibles

### ChannelSetupStates

Gestiona la configuración de IDs de canales VIP y gratuito.

**Estados**:
- `waiting_channel_id_or_forward`: Espera el ID del canal (número) o un mensaje reenviado desde el canal

**Flujo**:
1. Administrador selecciona "Configurar Canales" → "Canal VIP" o "Canal Free"
2. Bot solicita ID del canal o mensaje reenviado
3. Usuario envía ID numérico o reenvía mensaje del canal
4. Sistema valida y registra el canal

### PostSendingStates

Gestiona el flujo de envío de publicaciones a canales VIP y gratuito con reacciones opcionales.

**Estados**:
- `waiting_post_content`: Espera el contenido de la publicación a enviar (texto, foto, video, etc.)
- `waiting_reaction_decision`: Espera la decisión del admin sobre incluir reacciones (sí/no)
- `waiting_confirmation`: Espera confirmación final tras mostrar previsualización

**Flujo**:
1. Administrador selecciona "Enviar Publicación" desde menú VIP o Free
2. Bot solicita contenido → `waiting_post_content`
3. Si reacciones están configuradas para el canal: pregunta si incluir → `waiting_reaction_decision`
4. Sistema muestra previsualización exacta del formato final
5. Usuario confirma/envía o cancela → `waiting_confirmation`
6. Publicación enviada al canal o proceso cancelado, estado limpiado

### SubscriptionTierStates

Gestiona la creación y edición de tarifas de suscripción.

**Estados**:
- `waiting_tier_name`: Espera el nombre de la tarifa
- `waiting_tier_duration`: Espera la duración en días
- `waiting_tier_price`: Espera el precio en USD
- `waiting_tier_selection`: Espera la selección de tarifa para edición/eliminación

**Flujo**:
1. Administrador selecciona "Nueva Tarifa" en menú de tarifas
2. Bot solicita nombre → `waiting_tier_name`
3. Usuario envía nombre → Bot solicita duración → `waiting_tier_duration`
4. Usuario envía duración → Bot solicita precio → `waiting_tier_price`
5. Usuario envía precio → Tarifa creada, estado limpiado

### FreeConfigStates

**Estados**:
- `waiting_wait_time_minutes`: Espera el tiempo de espera en minutos para configuración gratuita

*(Posiblemente obsoleta, reemplazada por WaitTimeSetupStates)*

### WaitTimeSetupStates

Gestiona la configuración del tiempo de espera para solicitudes gratuitas.

**Estados**:
- `waiting_wait_time_minutes`: Espera el tiempo de espera en minutos

**Flujo**:
1. Administrador selecciona "Configurar Tiempo de Espera"
2. Bot solicita nuevo valor en minutos
3. Usuario envía valor → Sistema valida y actualiza configuración

### ReactionSetupStates

Gestiona la configuración de reacciones inline para canales.

**Estados**:
- `waiting_reactions_input`: Espera lista de emojis separados por coma

**Flujo**:
1. Administrador selecciona "Configurar Reacciones"
2. Bot solicita emojis separados por coma
3. Usuario envía emojis → Sistema valida y actualiza configuración

## Transiciones de Estados

### Creación de Tarifas
```
admin → config_tiers → tier_new → waiting_tier_name 
→ [usuario envía nombre] → waiting_tier_duration
→ [usuario envía duración] → waiting_tier_price
→ [usuario envía precio] → tarifa creada → estado limpiado
```

### Configuración de Canales
```
admin → config_channels_menu → setup_vip_select/setup_free_select 
→ waiting_channel_id_or_forward
→ [usuario envía ID o reenvía mensaje] → canal registrado → estado limpiado
```

### Configuración de Tiempo de Espera
```
admin → free_config → free_wait_time_config
→ waiting_wait_time_minutes
→ [usuario envía minutos] → tiempo actualizado → estado limpiado
```

### Configuración de Reacciones
```
admin → vip_config_reactions/free_config_reactions
→ waiting_reactions_input
→ [usuario envía emojis] → reacciones guardadas → estado limpiado
```

## Manejo de Errores

- Validación de datos en cada estado
- Limpieza de estado en caso de error
- Mensajes de error específicos para cada tipo de entrada inválida
- Verificación de permisos de administrador en cada paso del flujo

## Limpieza de Estados

Los estados se limpian explícitamente una vez completada la operación correspondiente usando `await state.clear()` para evitar conflictos con futuras interacciones.

## Almacenamiento de Datos Temporales

Durante los flujos FSM, se utilizan `state.update_data()` y `state.get_data()` para almacenar temporalmente información entre estados, como el tipo de canal o datos de tarifas en creación.