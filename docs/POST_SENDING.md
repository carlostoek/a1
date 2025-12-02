# Envío de Publicaciones con Reacciones

## Descripción General

El sistema de envío de publicaciones permite a los administradores enviar contenido a los canales VIP y gratuito con la opción de incluir botones de reacción. El sistema implementa una verificación previa para determinar si hay reacciones configuradas para el canal correspondiente y pregunta al administrador si desea incluirlas. El flujo incluye mejoras en el manejo de errores, validación de tipos y seguridad de tipos.

## Características

- **Envío a canales VIP y gratuito**: Funcionalidad disponible para ambos tipos de canales
- **Reacciones opcionales**: El sistema detecta reacciones configuradas y pregunta si incluirlas
- **Previsualización exacta**: Muestra una vista previa del formato final antes de enviar
- **Flujo de confirmación**: Botones de "Enviar" o "Cancelar" para confirmar la acción
- **Soporte multimedia**: Acepta texto, fotos, videos y otros tipos de contenido
- **Validación de tipo de canal**: Verificación robusta para prevenir publicación en canal incorrecto
- **Manejo mejorado de errores**: Control de errores específico en cada paso del proceso
- **Seguridad de tipos**: Anotaciones de tipo completas para prevenir errores de tipo

## Flujos de Usuario

### Envío a Canal VIP

1. Administrador selecciona "Gestión VIP" → "Enviar Publicación"
2. Sistema establece estado `PostSendingStates.waiting_post_content`
3. Administrador envía contenido (texto, foto, video, etc.)
4. Sistema verifica si hay reacciones configuradas para VIP:
   - Si hay reacciones: Pregunta "¿Deseas añadir los botones de reacción a esta publicación?" con opciones Sí/No
   - Si no hay reacciones: Continúa directamente al paso de previsualización
5. Si se selecciona "Sí" para reacciones: Sistema prepara botones de reacción usando el método compartido `get_reactions_for_channel`
6. Sistema muestra previsualización exacta del formato final al administrador
7. Sistema presenta botones de confirmación: "Enviar" o "Cancelar"
8. Si se selecciona "Enviar": Publicación se envía al canal VIP con reacciones si se incluyeron
9. Si se selecciona "Cancelar": Proceso se interrumpe y estado se limpia

### Envío a Canal Free

1. Administrador selecciona "Gestión Free" → "Enviar Publicación"
2. Sistema establece estado `PostSendingStates.waiting_post_content`
3. Administrador envía contenido (texto, foto, video, etc.)
4. Sistema verifica si hay reacciones configuradas para Free:
   - Si hay reacciones: Pregunta "¿Deseas añadir los botones de reacción a esta publicación?" con opciones Sí/No
   - Si no hay reacciones: Continúa directamente al paso de previsualización
5. Si se selecciona "Sí" para reacciones: Sistema prepara botones de reacción usando el método compartido `get_reactions_for_channel`
6. Sistema muestra previsualización exacta del formato final al administrador
7. Sistema presenta botones de confirmación: "Enviar" o "Cancelar"
8. Si se selecciona "Enviar": Publicación se envía al canal Free con reacciones si se incluyeron
9. Si se selecciona "Cancelar": Proceso se interrumpe y estado se limpia

## Estados FSM

### PostSendingStates

- `waiting_post_content`: Espera el contenido del post (texto, foto, video, etc.)
- `waiting_reaction_decision`: Espera la decisión del admin sobre incluir reacciones (sí/no)
- `waiting_confirmation`: Espera confirmación final tras mostrar previsualización

## Configuración de Reacciones

Las reacciones se configuran previamente para cada tipo de canal:

1. **Canal VIP**: Desde "Gestión VIP" → "Configurar" → "Configurar Reacciones"
2. **Canal Free**: Desde "Gestión Free" → "Configurar" → "Configurar Reacciones"

Formato: Lista de emojis separados por comas (ej: 👍,🔥,🚀). Máximo 10 emojis por canal.

## Implementación Técnica

### Servicio: ChannelManagementService

- Método: `broadcast_post(target_channel_type, message_id, from_chat_id, use_reactions, bot, session)`
- Copia el mensaje original al canal objetivo
- Si `use_reactions` es True, crea botones de reacción usando `MenuFactory.create_reaction_keyboard`

### Utilidad: MenuFactory

- Método: `create_reaction_keyboard(channel_type, reactions_list)`
- Crea un teclado inline con los emojis configurados como botones de reacción
- Botones se organizan en una sola fila

### Estados: PostSendingStates

- Implementado con Aiogram FSM
- Manejo de datos temporales entre estados usando `state.update_data()` y `state.get_data()`
- Limpieza automática del estado al completar o cancelar el proceso

## Seguridad

- Verificación de permisos de administrador en cada paso del flujo
- Validación del tipo de canal (VIP o Free) antes del envío
- Confirmación explícita antes de enviar la publicación
- Manejo de errores y rollback en caso de fallos

## Consideraciones

- El sistema de reacciones es opcional: Si no hay reacciones configuradas, el proceso de envío es directo
- La previsualización muestra exactamente cómo se verá la publicación en el canal destino
- Las reacciones se configuran por tipo de canal, no por publicación individual
- El bot debe tener permisos de administrador en los canales objetivo para enviar publicaciones