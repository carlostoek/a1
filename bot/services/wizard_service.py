from typing import Type, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.wizards.core import BaseWizard, WizardContext, WizardStep
from bot.services.gamification_service import GamificationService


class WizardStates(StatesGroup):
    active = State()


class WizardService:
    def __init__(self):
        self.active_wizards: Dict[int, WizardContext] = {}  # user_id -> context
        # Register wizard classes for lookup
        self.wizard_registry: Dict[str, Type[BaseWizard]] = {}
        self._register_default_wizards()

    def _register_default_wizards(self):
        """Register default wizards in the system."""
        from bot.wizards.rank_wizard import RankWizard
        self.wizard_registry["RankWizard"] = RankWizard

    def register_wizard(self, name: str, wizard_class: Type[BaseWizard]):
        """Register a new wizard in the system."""
        self.wizard_registry[name] = wizard_class

    async def start_wizard(self, user_id: int, wizard_class: Type[BaseWizard],
                          fsm_context: FSMContext, return_context: Optional[dict] = None, services: Optional[Any] = None):
        """Inicializa contexto y guarda en FSM."""
        wizard = wizard_class()
        context = WizardContext(
            wizard_id=wizard_class.__name__,
            current_step_index=0,
            data={},
            return_context=return_context
        )

        self.active_wizards[user_id] = context
        await fsm_context.set_state(WizardStates.active)
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
                    result = await self._process_wizard_completion(user_id, context, fsm_context, session)
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
                result = await self._process_wizard_completion(user_id, context, fsm_context, session)
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
        """Helper to get wizard instance by ID using registry."""
        if wizard_id in self.wizard_registry:
            wizard_class = self.wizard_registry[wizard_id]
            return wizard_class()
        return None

    async def _process_wizard_completion(self, user_id: int, context: WizardContext, fsm_context: FSMContext, session: AsyncSession):
        """Helper to process wizard completion and create rank if needed."""
        wizard = self._get_wizard_instance_by_id(context.wizard_id)
        if not wizard:
            return None

        result = await wizard.on_complete(context, session)

        # If the result contains rank data, create the rank using services
        if isinstance(result, dict) and 'name' in result:
            fsm_data = await fsm_context.get_data()
            services = fsm_data.get('services')

            if services and hasattr(services, 'gamification'):
                from bot.services.gamification_service import GamificationService
                gamification_service: GamificationService = services.gamification

                if gamification_service:
                    rank = await gamification_service.create_rank(
                        name=result['name'],
                        min_points=result['min_points'],
                        session=session,
                        reward_vip_days=result.get('reward_vip_days', 0)
                    )
                    result = rank

        del self.active_wizards[user_id]
        await fsm_context.clear()
        return result

    async def process_callback_input(self, user_id: int, callback_data: str,
                                   fsm_context: FSMContext, session: AsyncSession):
        """Procesa entrada de callback durante un wizard."""
        if user_id not in self.active_wizards:
            return None, "No active wizard found"

        context = self.active_wizards[user_id]
        wizard = self._get_wizard_instance_by_id(context.wizard_id)
        if not wizard:
            return None, "Wizard not found"

        # Let the wizard handle its own callback
        # This uses a method that the BaseWizard class should implement for callback processing
        result = await wizard.process_callback(context, callback_data, self)
        if result is None:
            return None, "Callback not handled for this step"

        # Update context after processing
        await fsm_context.update_data(wizard_context=context)

        # Check if the wizard is completed after callback processing
        if result.get('completed'):
            completion_result = await self._process_wizard_completion(user_id, context, fsm_context, session)
            return completion_result, "Wizard completed"

        # Otherwise, return the next step to render
        next_step_index = result.get('next_step_index', context.current_step_index)
        if next_step_index < len(wizard.steps):
            context.current_step_index = next_step_index
            await fsm_context.update_data(wizard_context=context)
            next_step = wizard.steps[context.current_step_index]
            message_text = next_step.text_provider(context)
            keyboard = next_step.keyboard_provider(context) if next_step.keyboard_provider else None
            status = result.get('status', 'Callback processed')
            return {"text": message_text, "keyboard": keyboard}, status
        else:
            # If no more steps after callback, complete the wizard
            completion_result = await self._process_wizard_completion(user_id, context, fsm_context, session)
            return completion_result, "Wizard completed"