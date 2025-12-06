from bot.wizards.core import BaseWizard, WizardStep, WizardContext
from bot.wizards.validators import CommonValidators
from bot.wizards.ui_renderer import WizardUIRenderer
from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup


class RankWizard(BaseWizard):
    def get_steps(self) -> List[WizardStep]:
        # Static definition of steps
        # In the callback handler, we manage conditional flow
        return [
            # Paso 1: Nombre
            WizardStep(
                name="rank_name",
                text_provider=lambda ctx: "🧙‍♂️ **Nuevo Rango**\n\n¿Cómo se llamará? (Ej: Veterano)",
                validator=CommonValidators.text_min_length(3),
                on_valid=lambda ctx, val: ctx.data.update(name=val)
            ),
            # Paso 2: Puntos
            WizardStep(
                name="rank_points",
                text_provider=lambda ctx: f"Perfecto, **{ctx.data['name']}**.\n¿Cuántos puntos se requieren?",
                validator=CommonValidators.is_integer(0),
                on_valid=lambda ctx, val: ctx.data.update(points=val)
            ),
            # Paso 3: VIP (Sí/No con teclado)
            WizardStep(
                name="ask_vip",
                text_provider=lambda ctx: "¿Este rango otorga **Días VIP**?",
                keyboard_provider=lambda ctx: WizardUIRenderer.yes_no_keyboard(),
                # Nota: Aquí el handler de callback procesará la respuesta
            ),
            # Paso 4: Días VIP (si se respondió Sí en el paso anterior)
            WizardStep(
                name="vip_days",
                text_provider=lambda ctx: "¿Cuántos días VIP se otorgan?",
                validator=CommonValidators.is_integer(0),
                on_valid=lambda ctx, val: ctx.data.update(vip_days=val)
            ),
        ]

    async def on_complete(self, context: WizardContext, session):
        # Lógica final de guardado en BD usando GamificationService
        # The services will be passed in context or retrieved from a global service container
        from bot.services.gamification_service import GamificationService

        # Extract the data from context
        name = context.data.get('name')
        points = context.data.get('points')

        # The VIP status should be stored as True/False from the callback handler
        # If user selected "yes" for VIP and then provided VIP days, we use that
        if context.data.get('vip', False) and 'vip_days' in context.data:  # If user said yes to VIP and provided days
            reward_vip_days = context.data.get('vip_days', 0)
        else:
            # If user said no to VIP or didn't enter days, default to 0
            reward_vip_days = 0

        # Create the new rank using GamificationService
        # We'll assume the service is injected somehow - this will be handled by the handler
        # For now, return the data to be handled by the calling function
        rank_data = {
            'name': name,
            'min_points': points,
            'reward_vip_days': reward_vip_days
        }

        return rank_data