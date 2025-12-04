#!/usr/bin/env python3
"""
Script de demostración del Sexy Logger.
Muestra todos los tipos de logs disponibles con colores y emojis.
"""
import asyncio
import time
from bot.utils.sexy_logger import get_logger, SexyLogger
import logging


def demo_basic_logs():
    """Demuestra los logs básicos estándar."""
    print("\n" + "="*60)
    print("📋 LOGS BÁSICOS ESTÁNDAR")
    print("="*60 + "\n")

    logger = get_logger("BasicDemo")

    logger.debug("Este es un mensaje de DEBUG - útil para depuración")
    time.sleep(0.3)
    logger.info("Este es un mensaje de INFO - información general")
    time.sleep(0.3)
    logger.warning("Este es un mensaje de WARNING - advertencia")
    time.sleep(0.3)
    logger.error("Este es un mensaje de ERROR - algo salió mal")
    time.sleep(0.3)
    logger.critical("Este es un mensaje CRITICAL - error crítico del sistema")


def demo_custom_logs():
    """Demuestra los logs personalizados con estilos especiales."""
    print("\n" + "="*60)
    print("✨ LOGS PERSONALIZADOS CON ESTILOS ESPECIALES")
    print("="*60 + "\n")

    logger = get_logger("CustomDemo")

    logger.startup("Bot iniciando - cargando módulos...")
    time.sleep(0.3)
    logger.success("Conexión exitosa a la base de datos")
    time.sleep(0.3)
    logger.database("Ejecutando query: SELECT * FROM users")
    time.sleep(0.3)
    logger.api("Llamada API: GET /api/v1/users")
    time.sleep(0.3)
    logger.event("Evento recibido: user.registered")
    time.sleep(0.3)
    logger.task("Procesando tarea en segundo plano")
    time.sleep(0.3)
    logger.user("Usuario @johndoe realizó login")
    time.sleep(0.3)
    logger.network("Conectando al servidor remoto...")
    time.sleep(0.3)
    logger.security("Intento de acceso no autorizado detectado")
    time.sleep(0.3)
    logger.shutdown("Bot apagándose - cerrando conexiones...")


def demo_with_exceptions():
    """Demuestra cómo se ven los logs con excepciones."""
    print("\n" + "="*60)
    print("💥 LOGS CON EXCEPCIONES")
    print("="*60 + "\n")

    logger = get_logger("ExceptionDemo")

    try:
        # Simular un error
        result = 10 / 0
    except ZeroDivisionError as e:
        logger.error("Error en la operación matemática", exc_info=True)


def demo_different_configs():
    """Demuestra diferentes configuraciones del logger."""
    print("\n" + "="*60)
    print("⚙️  DIFERENTES CONFIGURACIONES")
    print("="*60 + "\n")

    # Logger sin colores
    print("\n🔹 Logger sin colores:")
    logger_no_color = SexyLogger("NoColor", use_colors=False)
    logger_no_color.info("Este mensaje no tiene colores")
    logger_no_color.success("Operación exitosa sin colores")

    time.sleep(0.5)

    # Logger sin timestamp
    print("\n🔹 Logger sin timestamp:")
    logger_no_time = SexyLogger("NoTime", show_time=False)
    logger_no_time.info("Este mensaje no tiene timestamp")
    logger_no_time.warning("Advertencia sin timestamp")

    time.sleep(0.5)

    # Logger sin nombre
    print("\n🔹 Logger sin nombre:")
    logger_no_name = SexyLogger("NoName", show_name=False)
    logger_no_name.info("Este mensaje no muestra el nombre del logger")
    logger_no_name.error("Error sin nombre del logger")

    time.sleep(0.5)

    # Logger minimalista
    print("\n🔹 Logger minimalista (sin tiempo ni nombre):")
    logger_minimal = SexyLogger("Minimal", show_time=False, show_name=False)
    logger_minimal.startup("Modo minimalista activado")
    logger_minimal.success("¡Todo funcionando!")


def demo_log_levels():
    """Demuestra el filtrado por niveles de log."""
    print("\n" + "="*60)
    print("🎚️  FILTRADO POR NIVELES")
    print("="*60 + "\n")

    print("🔹 Logger con nivel WARNING (solo WARNING, ERROR, CRITICAL):")
    logger_warn = SexyLogger("WarnLevel", level=logging.WARNING)
    logger_warn.debug("Este DEBUG no se verá")
    logger_warn.info("Este INFO no se verá")
    logger_warn.warning("Este WARNING sí se ve")
    logger_warn.error("Este ERROR sí se ve")

    time.sleep(0.5)

    print("\n🔹 Logger con nivel DEBUG (se ven todos):")
    logger_debug = SexyLogger("DebugLevel", level=logging.DEBUG)
    logger_debug.debug("Este DEBUG ahora sí se ve")
    logger_debug.info("Este INFO también se ve")


async def demo_async_context():
    """Demuestra el uso del logger en contexto asíncrono."""
    print("\n" + "="*60)
    print("⏱️  USO EN CONTEXTO ASÍNCRONO")
    print("="*60 + "\n")

    logger = get_logger("AsyncDemo")

    logger.task("Iniciando tarea asíncrona 1...")
    await asyncio.sleep(0.5)
    logger.success("Tarea 1 completada")

    logger.task("Iniciando tarea asíncrona 2...")
    await asyncio.sleep(0.5)
    logger.success("Tarea 2 completada")

    logger.task("Iniciando tarea asíncrona 3...")
    await asyncio.sleep(0.5)
    logger.success("Tarea 3 completada")


def demo_real_world_scenario():
    """Simula un escenario del mundo real."""
    print("\n" + "="*60)
    print("🌍 ESCENARIO DEL MUNDO REAL")
    print("="*60 + "\n")

    logger = get_logger("BotManager")

    # Simular inicio de bot
    logger.startup("Iniciando Telegram Bot...")
    time.sleep(0.3)

    logger.database("Conectando a la base de datos...")
    time.sleep(0.3)
    logger.success("Conexión a DB establecida")
    time.sleep(0.3)

    logger.api("Validando token de Telegram API...")
    time.sleep(0.3)
    logger.success("Token validado correctamente")
    time.sleep(0.3)

    logger.event("Registrando event handlers...")
    time.sleep(0.3)
    logger.success("15 handlers registrados")
    time.sleep(0.3)

    logger.task("Iniciando tareas en segundo plano...")
    time.sleep(0.3)
    logger.success("2 tareas iniciadas")
    time.sleep(0.3)

    logger.startup("Bot listo y escuchando eventos")
    time.sleep(1)

    # Simular actividad
    logger.user("Usuario @alice envió comando /start")
    time.sleep(0.3)
    logger.database("Query: SELECT * FROM users WHERE username='alice'")
    time.sleep(0.3)
    logger.user("Nuevo usuario registrado: @alice")
    time.sleep(0.3)

    logger.event("Procesando evento: new_subscription")
    time.sleep(0.3)
    logger.database("Insertando suscripción en DB...")
    time.sleep(0.3)
    logger.success("Suscripción creada exitosamente")
    time.sleep(0.3)

    # Simular un problema
    logger.warning("Cola de mensajes alcanzó el 80% de capacidad")
    time.sleep(0.3)
    logger.task("Iniciando limpieza de cola...")
    time.sleep(0.3)
    logger.success("Cola limpiada - espacio liberado")
    time.sleep(1)

    # Simular cierre
    logger.shutdown("Señal de apagado recibida")
    time.sleep(0.3)
    logger.task("Cancelando tareas en segundo plano...")
    time.sleep(0.3)
    logger.success("Tareas canceladas")
    time.sleep(0.3)
    logger.database("Cerrando conexiones a DB...")
    time.sleep(0.3)
    logger.shutdown("Bot apagado correctamente")


def main():
    """Función principal que ejecuta todas las demos."""
    print("\n" + "🎨"*30)
    print("✨ DEMOSTRACIÓN DEL SEXY LOGGER ✨")
    print("🎨"*30)

    # Ejecutar todas las demos
    demo_basic_logs()
    time.sleep(1)

    demo_custom_logs()
    time.sleep(1)

    demo_with_exceptions()
    time.sleep(1)

    demo_different_configs()
    time.sleep(1)

    demo_log_levels()
    time.sleep(1)

    # Demo asíncrona
    asyncio.run(demo_async_context())
    time.sleep(1)

    demo_real_world_scenario()

    # Mensaje final
    print("\n" + "="*60)
    print("✅ DEMOSTRACIÓN COMPLETADA")
    print("="*60)
    print("\n📚 Documentación rápida:")
    print("  - logger.debug()     : Mensajes de depuración")
    print("  - logger.info()      : Información general")
    print("  - logger.warning()   : Advertencias")
    print("  - logger.error()     : Errores")
    print("  - logger.critical()  : Errores críticos")
    print("  - logger.startup()   : Inicio de sistema")
    print("  - logger.shutdown()  : Apagado de sistema")
    print("  - logger.success()   : Operaciones exitosas")
    print("  - logger.database()  : Operaciones de BD")
    print("  - logger.api()       : Llamadas API")
    print("  - logger.event()     : Eventos del sistema")
    print("  - logger.task()      : Tareas en background")
    print("  - logger.user()      : Acciones de usuario")
    print("  - logger.network()   : Operaciones de red")
    print("  - logger.security()  : Eventos de seguridad")
    print("\n💡 Tip: Importa con 'from bot.utils.sexy_logger import get_logger'")
    print("💡 Uso: logger = get_logger(__name__)\n")


if __name__ == "__main__":
    main()
