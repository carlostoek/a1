from typing import Type, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.fsm.context import FSMContext
from bot.wizards.core import BaseWizard, WizardContext, WizardStep


class WizardService:
    def __init__(self):
        self.active_wizards: Dict[int, WizardContext] = {}  # user_id -> context

    async def start_wizard(self, user_id: int, wizard_class: Type[BaseWizard],
                          fsm_context: FSMContext, return_context: Optional[dict] = None, services=None):
        """Inicializa contexto y guarda en FSM."""
        wizard = wizard_class()
        context = WizardContext(
            wizard_id=wizard_class.__name__,
            current_step_index=0,
            data={},
            return_context=return_context
        )

        self.active_wizards[user_id] = context
        await fsm_context.set_state("wizard_active")  # Using a generic state
        await fsm_context.update_data(wizard_context=context, services=services)

    async def process_message_input(self, user_id: int, text: str,
                                   fsm_context: FSMContext, session: AsyncSession):
        """Procesa entrada de texto del usuario durante un wizard."""
        if user_id not in self.active_wizards:
            return None, "No active wizard found"

        context = self.active_wizards[user_id]
        wizard = self._get_wizard_instance_by_id(context.wizard_id)
        if not wizard:
            return None, "Wizard not found"

        current_step = wizard.steps[context.current_step_index]

        if current_step.validator:
            validated_value = current_step.validator(text)
            if validated_value is not None:
                # Valor válido, ejecutar callback y avanzar al siguiente paso
                if current_step.on_valid:
                    current_step.on_valid(context, validated_value)

                context.current_step_index += 1

                # Verificar si hemos completado todos los pasos
                if context.current_step_index >= len(wizard.steps):
                    # Get services from FSM context
                    fsm_data = await fsm_context.get_data()
                    services = fsm_data.get('services')
                    result = await wizard.on_complete(context, session)

                    # If the result contains rank data, create the rank using services
                    if isinstance(result, dict) and 'name' in result:
                        from bot.services.gamification_service import GamificationService
                        gamification_service: GamificationService = services.gamification if services else None

                        if gamification_service:
                            rank = await gamification_service.create_rank(
                                name=result['name'],
                                min_points=result['min_points'],
                                session=session,
                                reward_vip_days=result.get('reward_vip_days', 0)
                            )
                            result = rank  # Update result with the created rank

                    del self.active_wizards[user_id]  # Limpiar contexto
                    await fsm_context.clear()
                    return result, "Wizard completed"

                # Actualizar contexto en FSM
                await fsm_context.update_data(wizard_context=context)

                # Renderizar siguiente paso
                next_step = wizard.steps[context.current_step_index]
                message_text = next_step.text_provider(context)
                keyboard = next_step.keyboard_provider(context) if next_step.keyboard_provider else None
                return {"text": message_text, "keyboard": keyboard}, "Valid input processed"
            else:
                # Valor inválido, re-renderizar con mensaje de error
                error_message = "❌ Valor inválido. Por favor, inténtalo de nuevo."
                message_text = current_step.text_provider(context)
                keyboard = current_step.keyboard_provider(context) if current_step.keyboard_provider else None
                return {"text": message_text, "keyboard": keyboard, "error": error_message}, "Invalid input"
        else:
            # Si no hay validador, simplemente avanzar al siguiente paso
            context.current_step_index += 1
            if context.current_step_index >= len(wizard.steps):
                # Get services from FSM context
                fsm_data = await fsm_context.get_data()
                services = fsm_data.get('services')
                result = await wizard.on_complete(context, session)

                # If the result contains rank data, create the rank using services
                if isinstance(result, dict) and 'name' in result:
                    from bot.services.gamification_service import GamificationService
                    gamification_service: GamificationService = services.gamification if services else None

                    if gamification_service:
                        rank = await gamification_service.create_rank(
                            name=result['name'],
                            min_points=result['min_points'],
                            session=session,
                            reward_vip_days=result.get('reward_vip_days', 0)
                        )
                        result = rank  # Update result with the created rank

                del self.active_wizards[user_id]  # Limpiar contexto
                await fsm_context.clear()
                return result, "Wizard completed"

            # Actualizar contexto en FSM
            await fsm_context.update_data(wizard_context=context)

            # Renderizar siguiente paso
            next_step = wizard.steps[context.current_step_index]
            message_text = next_step.text_provider(context)
            keyboard = next_step.keyboard_provider(context) if next_step.keyboard_provider else None
            return {"text": message_text, "keyboard": keyboard}, "Step advanced"

    async def render_current_step(self, user_id: int, fsm_context: FSMContext):
        """Envía mensaje/teclado al usuario."""
        if user_id not in self.active_wizards:
            return None
        
        context = self.active_wizards[user_id]
        wizard = self._get_wizard_instance_by_id(context.wizard_id)
        if not wizard:
            return None
        
        current_step = wizard.steps[context.current_step_index]
        message_text = current_step.text_provider(context)
        keyboard = current_step.keyboard_provider(context) if current_step.keyboard_provider else None
        
        return {"text": message_text, "keyboard": keyboard}

    def _get_wizard_instance_by_id(self, wizard_id: str) -> Optional[BaseWizard]:
        """Helper to get wizard instance by ID."""
        # This is a simplified approach - in a real implementation, you'd want to register
        # wizard classes properly and look them up
        from bot.wizards.rank_wizard import RankWizard

        if wizard_id == "RankWizard":
            return RankWizard()
        return None

    async def process_callback_input(self, user_id: int, callback_data: str,
                                   fsm_context: FSMContext, session: AsyncSession):
        """Procesa entrada de callback durante un wizard."""
        if user_id not in self.active_wizards:
            return None, "No active wizard found"

        context = self.active_wizards[user_id]
        wizard = self._get_wizard_instance_by_id(context.wizard_id)
        if not wizard:
            return None, "Wizard not found"

        current_step = wizard.steps[context.current_step_index]

        # Handle VIP question callback
        if current_step.name == "ask_vip":
            if callback_data in ["yes", "no"]:
                # Save the VIP information in context
                is_vip = (callback_data == "yes")
                context.data.update(vip=is_vip)

                # If VIP is yes, we need to ask for days
                # If VIP is no, we can skip the VIP days step
                if is_vip:
                    # Advance to next step to ask for VIP days
                    context.current_step_index += 1

                    # Update FSM context
                    await fsm_context.update_data(wizard_context=context)

                    # Render the next step which should ask for VIP days
                    if context.current_step_index < len(wizard.steps):
                        next_step = wizard.steps[context.current_step_index]
                        message_text = next_step.text_provider(context)
                        keyboard = next_step.keyboard_provider(context) if next_step.keyboard_provider else None
                        return {"text": message_text, "keyboard": keyboard}, "Waiting for VIP days"
                    else:
                        # If no more steps, complete the wizard
                        fsm_data = await fsm_context.get_data()
                        services = fsm_data.get('services')
                        result = await wizard.on_complete(context, session)

                        # If the result contains rank data, create the rank using services
                        if isinstance(result, dict) and 'name' in result:
                            from bot.services.gamification_service import GamificationService
                            gamification_service: GamificationService = services.gamification if services else None

                            if gamification_service:
                                rank = await gamification_service.create_rank(
                                    name=result['name'],
                                    min_points=result['min_points'],
                                    session=session,
                                    reward_vip_days=result.get('reward_vip_days', 0)
                                )
                                result = rank  # Update result with the created rank

                        del self.active_wizards[user_id]  # Limpiar contexto
                        await fsm_context.clear()
                        return result, "Wizard completed"
                else:
                    # If no VIP, skip to next step - if there are further steps, we'll need to handle
                    # conditional logic differently. For now, assume no more steps after VIP days.
                    # We need to advance past the VIP days step
                    if context.current_step_index + 1 < len(wizard.steps):
                        context.current_step_index += 1  # Skip the VIP days step

                        # If we're now at the end (no more steps), complete the wizard
                        if context.current_step_index >= len(wizard.steps):
                            fsm_data = await fsm_context.get_data()
                            services = fsm_data.get('services')
                            result = await wizard.on_complete(context, session)

                            # If the result contains rank data, create the rank using services
                            if isinstance(result, dict) and 'name' in result:
                                from bot.services.gamification_service import GamificationService
                                gamification_service: GamificationService = services.gamification if services else None

                                if gamification_service:
                                    rank = await gamification_service.create_rank(
                                        name=result['name'],
                                        min_points=result['min_points'],
                                        session=session,
                                        reward_vip_days=result.get('reward_vip_days', 0)
                                    )
                                    result = rank  # Update result with the created rank

                            del self.active_wizards[user_id]  # Limpiar contexto
                            await fsm_context.clear()
                            return result, "Wizard completed"
                        else:
                            # If there are more steps after VIP days, move to the next one
                            next_step = wizard.steps[context.current_step_index]
                            message_text = next_step.text_provider(context)
                            keyboard = next_step.keyboard_provider(context) if next_step.keyboard_provider else None
                            await fsm_context.update_data(wizard_context=context)
                            return {"text": message_text, "keyboard": keyboard}, "Moved to next step"
                    else:
                        # If there are no more steps, complete the wizard
                        fsm_data = await fsm_context.get_data()
                        services = fsm_data.get('services')
                        result = await wizard.on_complete(context, session)

                        # If the result contains rank data, create the rank using services
                        if isinstance(result, dict) and 'name' in result:
                            from bot.services.gamification_service import GamificationService
                            gamification_service: GamificationService = services.gamification if services else None

                            if gamification_service:
                                rank = await gamification_service.create_rank(
                                    name=result['name'],
                                    min_points=result['min_points'],
                                    session=session,
                                    reward_vip_days=result.get('reward_vip_days', 0)
                                )
                                result = rank  # Update result with the created rank

                        del self.active_wizards[user_id]  # Limpiar contexto
                        await fsm_context.clear()
                        return result, "Wizard completed"
            else:
                return None, "Invalid callback"
        else:
            return None, "Callback not handled for this step"