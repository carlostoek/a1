# CHANGELOG

## [No Version] - 2025-02-11

### Added
- Implementación de envío de publicaciones con reacciones opcionales a canales VIP y gratuitos
- Implementación de configuración de reacciones inline personalizadas para canales VIP y gratuitos
- Implementación de MenuFactory para UI estandarizada en menús
- Implementación de tiempos de espera personalizados para solicitudes de canales gratuitos
- Sistema de gestión de tarifas de suscripción con creación, edición y eliminación
- Configuración de canales VIP y gratuitos con validación de administrador
- Sistema de tokens de suscripción VIP con generación y canje
- Sistema de acceso gratuito con colas y tiempos de espera
- Gestión de roles de usuario (free, vip, admin)
- Estadísticas de usuarios y solicitudes
- Middlewares de autenticación y base de datos
- Base de datos con SQLAlchemy y modelos ORM
- Estados FSM para flujos de configuración
- Servicios de suscripción, canales y configuración

### Changed
- Alineación de tiempo de espera para canales gratuitos a especificaciones
- Mejora del flujo de bienvenida para usuarios gratuitos (sin enlace de invitación)
- Mejora del flujo de registro de canales (VIP & Free)
- Implementación de actualización robusta de configuración con mensajes de error
- Actualización del flujo de interacción con suscriptores VIP incluyendo generación de enlaces de invitación
- Refactorización a niveles de tokens basados en suscripción
- Implementación de CRUD para SubscriptionTier en ConfigService
- **PR12**: Mejora del flujo de envío de publicaciones con mejor manejo de errores
- **PR12**: Consolidación de código duplicado en servicios
- **PR12**: Mejora de la seguridad de tipos con anotaciones apropiadas
- **PR12**: Mejora del manejo de excepciones en servicios y handlers
- **PR12**: Implementación de método compartido para obtener reacciones en ConfigService
- **PR12**: Reorganización de importaciones para seguir estilo PEP 8
- **PR12**: Mejora de la validación de tipo de canal para prevenir publicación en canal incorrecto

### Fixed
- Resolución de problemas de comparación de datetime y atributos de configuración
- Manejo robusto de errores para generación de enlaces de invitación
- Resolución de problemas en actualización de configuración y parseo de mensajes de error
- Correcciones de estilo y comentarios en código
- Solución de problemas de inicialización de base de datos
- **PR12**: Corrección de problemas en el servicio de configuración con funciones sueltas
- **PR12**: Mejora de la validación de tipos de canales en servicios