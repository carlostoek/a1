"""
Banner ASCII art para el inicio del bot.
Muestra información del sistema de forma visualmente atractiva.
"""
from bot.utils.sexy_logger import Colors


def get_banner() -> str:
    """
    Retorna el banner ASCII art del bot.

    Returns:
        str: Banner formateado con colores ANSI
    """
    banner = f"""
{Colors.BRIGHT_CYAN}╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║  {Colors.BRIGHT_MAGENTA}████████╗███████╗██╗     ███████╗ ██████╗ ██████╗  █████╗ ███╗   ███╗{Colors.BRIGHT_CYAN}  ║
║  {Colors.BRIGHT_MAGENTA}╚══██╔══╝██╔════╝██║     ██╔════╝██╔════╝ ██╔══██╗██╔══██╗████╗ ████║{Colors.BRIGHT_CYAN}  ║
║  {Colors.BRIGHT_MAGENTA}   ██║   █████╗  ██║     █████╗  ██║  ███╗██████╔╝███████║██╔████╔██║{Colors.BRIGHT_CYAN}  ║
║  {Colors.BRIGHT_MAGENTA}   ██║   ██╔══╝  ██║     ██╔══╝  ██║   ██║██╔══██╗██╔══██║██║╚██╔╝██║{Colors.BRIGHT_CYAN}  ║
║  {Colors.BRIGHT_MAGENTA}   ██║   ███████╗███████╗███████╗╚██████╔╝██║  ██║██║  ██║██║ ╚═╝ ██║{Colors.BRIGHT_CYAN}  ║
║  {Colors.BRIGHT_MAGENTA}   ╚═╝   ╚══════╝╚══════╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝{Colors.BRIGHT_CYAN}  ║
║                                                                      ║
║  {Colors.BRIGHT_WHITE}██╗   ██╗██╗██████╗     ██████╗  ██████╗ ████████╗                  {Colors.BRIGHT_CYAN}║
║  {Colors.BRIGHT_WHITE}██║   ██║██║██╔══██╗    ██╔══██╗██╔═══██╗╚══██╔══╝                  {Colors.BRIGHT_CYAN}║
║  {Colors.BRIGHT_WHITE}██║   ██║██║██████╔╝    ██████╔╝██║   ██║   ██║                     {Colors.BRIGHT_CYAN}║
║  {Colors.BRIGHT_WHITE}╚██╗ ██╔╝██║██╔═══╝     ██╔══██╗██║   ██║   ██║                     {Colors.BRIGHT_CYAN}║
║  {Colors.BRIGHT_WHITE} ╚████╔╝ ██║██║         ██████╔╝╚██████╔╝   ██║                     {Colors.BRIGHT_CYAN}║
║  {Colors.BRIGHT_WHITE}  ╚═══╝  ╚═╝╚═╝         ╚═════╝  ╚═════╝    ╚═╝                     {Colors.BRIGHT_CYAN}║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝{Colors.RESET}

{Colors.BRIGHT_YELLOW}    🤖 Bot de Administración de Telegram                                {Colors.RESET}
{Colors.BRIGHT_GREEN}    ✨ Sistema de Suscripciones VIP y Gestión de Canales               {Colors.RESET}
{Colors.DIM}    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  {Colors.RESET}
"""
    return banner


def print_banner():
    """Imprime el banner en la consola."""
    print(get_banner())


def print_system_info(bot_username: str = None, admin_count: int = 0):
    """
    Imprime información del sistema.

    Args:
        bot_username: Nombre de usuario del bot
        admin_count: Número de administradores configurados
    """
    info = f"""
{Colors.BRIGHT_CYAN}    ╭─────────────────────────────────────────────────────────────────╮{Colors.RESET}
{Colors.BRIGHT_CYAN}    │{Colors.RESET} {Colors.BRIGHT_WHITE}📊 INFORMACIÓN DEL SISTEMA{Colors.RESET}                                      {Colors.BRIGHT_CYAN}│{Colors.RESET}
{Colors.BRIGHT_CYAN}    ├─────────────────────────────────────────────────────────────────┤{Colors.RESET}
"""

    if bot_username:
        info += f"{Colors.BRIGHT_CYAN}    │{Colors.RESET}   🤖 Bot: {Colors.BRIGHT_GREEN}@{bot_username}{Colors.RESET}                                         {Colors.BRIGHT_CYAN}│{Colors.RESET}\n"

    info += f"""{Colors.BRIGHT_CYAN}    │{Colors.RESET}   👥 Administradores: {Colors.BRIGHT_YELLOW}{admin_count}{Colors.RESET}                                    {Colors.BRIGHT_CYAN}│{Colors.RESET}
{Colors.BRIGHT_CYAN}    │{Colors.RESET}   🗄️  Base de datos: {Colors.BRIGHT_GREEN}SQLite{Colors.RESET}                                    {Colors.BRIGHT_CYAN}│{Colors.RESET}
{Colors.BRIGHT_CYAN}    │{Colors.RESET}   🔧 Framework: {Colors.BRIGHT_MAGENTA}Aiogram 3.x{Colors.RESET}                                    {Colors.BRIGHT_CYAN}│{Colors.RESET}
{Colors.BRIGHT_CYAN}    │{Colors.RESET}   ✨ Sexy Logger: {Colors.BRIGHT_GREEN}Activado{Colors.RESET}                                     {Colors.BRIGHT_CYAN}│{Colors.RESET}
{Colors.BRIGHT_CYAN}    ╰─────────────────────────────────────────────────────────────────╯{Colors.RESET}
"""
    print(info)


def print_features():
    """Imprime las características principales del bot."""
    features = f"""
{Colors.BRIGHT_CYAN}    ╭─────────────────────────────────────────────────────────────────╮{Colors.RESET}
{Colors.BRIGHT_CYAN}    │{Colors.RESET} {Colors.BRIGHT_WHITE}🎯 CARACTERÍSTICAS PRINCIPALES{Colors.RESET}                                 {Colors.BRIGHT_CYAN}│{Colors.RESET}
{Colors.BRIGHT_CYAN}    ├─────────────────────────────────────────────────────────────────┤{Colors.RESET}
{Colors.BRIGHT_CYAN}    │{Colors.RESET}   ✅ Sistema de suscripciones VIP                             {Colors.BRIGHT_CYAN}│{Colors.RESET}
{Colors.BRIGHT_CYAN}    │{Colors.RESET}   ✅ Gestión de canales (VIP y Gratuitos)                     {Colors.BRIGHT_CYAN}│{Colors.RESET}
{Colors.BRIGHT_CYAN}    │{Colors.RESET}   ✅ Generación y canje de tokens                             {Colors.BRIGHT_CYAN}│{Colors.RESET}
{Colors.BRIGHT_CYAN}    │{Colors.RESET}   ✅ Sistema de gamificación con puntos y rangos              {Colors.BRIGHT_CYAN}│{Colors.RESET}
{Colors.BRIGHT_CYAN}    │{Colors.RESET}   ✅ Envío de publicaciones con reacciones                    {Colors.BRIGHT_CYAN}│{Colors.RESET}
{Colors.BRIGHT_CYAN}    │{Colors.RESET}   ✅ Sistema de recompensas automáticas                       {Colors.BRIGHT_CYAN}│{Colors.RESET}
{Colors.BRIGHT_CYAN}    │{Colors.RESET}   ✅ Estadísticas y análisis avanzado                         {Colors.BRIGHT_CYAN}│{Colors.RESET}
{Colors.BRIGHT_CYAN}    │{Colors.RESET}   ✅ Event Bus para comunicación entre módulos                {Colors.BRIGHT_CYAN}│{Colors.RESET}
{Colors.BRIGHT_CYAN}    ╰─────────────────────────────────────────────────────────────────╯{Colors.RESET}
"""
    print(features)


def print_startup_complete():
    """Imprime mensaje de inicio completado."""
    message = f"""
{Colors.BRIGHT_GREEN}    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║           🚀 {Colors.BRIGHT_WHITE}BOT INICIADO Y LISTO PARA RECIBIR EVENTOS{Colors.BRIGHT_GREEN}         ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝{Colors.RESET}
"""
    print(message)


def print_shutdown():
    """Imprime mensaje de apagado."""
    message = f"""
{Colors.BRIGHT_RED}    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║                 🛑 {Colors.BRIGHT_WHITE}BOT APAGÁNDOSE CORRECTAMENTE{Colors.BRIGHT_RED}                  ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝{Colors.RESET}
"""
    print(message)


def print_separator():
    """Imprime un separador visual."""
    print(f"{Colors.DIM}    {'─' * 70}{Colors.RESET}\n")
