import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from aiogram.exceptions import TelegramAPIError
from typing import Dict, Any, Optional


class NotificationService:
    # ⚠️ Plantillas base para el sistema de Gamificación/Alertas
    NOTIFICATION_TEMPLATES: Dict[str, str] = {
        "welcome_gamification": "🎉 **¡Bienvenido a la Gamificación!**\nHas ganado tus primeros {points} puntos. Completa misiones para subir de rango.",
        "score_update": "🏆 **Actualización de Puntaje:**\n¡Has ganado {points} puntos por tu actividad! Puntaje total: {total_points}.",
        "reward_unlocked": "🎁 **Recompensa Desbloqueada:**\n¡Felicitaciones! Has alcanzado el rango **{rank}** y desbloqueado {reward}.",
        "rank_up": "🏆 **¡Felicidades!**\nHas subido de rango: **{old_rank}** → **{new_rank}**",
        "vip_reward": "👑 **¡Recompensa de Rango!**\nHas ganado **{days} días** de acceso VIP. Tu nueva fecha de expiración es: **{date}**",
        "pack_reward": "📦 **¡Pack Desbloqueado!**\nAquí tienes tu recompensa **'{pack_name}'** por alcanzar el rango **{rank_name}**.",
        "vip_expiration_warning": "🚨 **Aviso VIP:**\nTu suscripción VIP expira en {days} días. ¡No te quedes fuera!",
        "generic_alert": "📢 **Alerta:** {message}"
    }

    def __init__(self, bot: Bot):
        # La instancia del bot debe ser inyectada al servicio.
        self.bot = bot

    async def send_notification(
        self,
        user_id: int,
        template_name: str,
        context_data: Optional[Dict[str, Any]] = None,
        reply_markup: Optional[InlineKeyboardMarkup] = None
    ) -> bool:
        """
        Envía una notificación al usuario basándose en una plantilla.
        """
        if template_name not in self.NOTIFICATION_TEMPLATES:
            # Opción de fallback si la plantilla no existe
            template = self.NOTIFICATION_TEMPLATES.get("generic_alert", "Alerta: {message}")
            context_data = {"message": f"Error: Plantilla '{template_name}' no encontrada."}
        else:
            template = self.NOTIFICATION_TEMPLATES[template_name]

        # Formatear el mensaje usando los datos de contexto
        try:
            message_text = template.format(**(context_data or {}))
        except KeyError as e:
            # Error de formato si falta una variable en el contexto
            message_text = f"🚨 Error de formato en plantilla '{template_name}': Falta la variable {e}"
        except Exception as e:
            # Otros errores de formato
            message_text = f"🚨 Error de formato en plantilla '{template_name}': {str(e)}"

        # Enviar el mensaje
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            return True
        except TelegramAPIError as e:
            # Manejo específico de errores de la API de Telegram
            logging.error(f"Telegram API error al enviar notificación a {user_id}: {e}")
            return False
        except Exception as e:
            # Manejo de otros errores
            logging.error(f"Error desconocido al enviar notificación a {user_id}: {e}")
            return False