from dataclasses import dataclass, field
from typing import Callable, Any, Optional, List, Union
from aiogram.types import InlineKeyboardMarkup, Message
from enum import Enum


# Contexto tipado (Estado del Wizard)
@dataclass
class WizardContext:
    wizard_id: str
    current_step_index: int = 0
    data: dict = field(default_factory=dict)
    return_context: Optional[dict] = None  # Para flujos anidados


# Definición de un Paso
@dataclass
class WizardStep:
    name: str
    text_provider: Callable[[WizardContext], str]  # Función que retorna el texto del paso
    keyboard_provider: Optional[Callable[[WizardContext], InlineKeyboardMarkup]] = None
    validator: Optional[Callable[[Any], Union[Any, None]]] = None  # Retorna valor limpio o None si falla
    on_valid: Optional[Callable[[WizardContext, Any], None]] = None  # Callback para guardar datos


# Clase Base Abstracta
class BaseWizard:
    def __init__(self):
        self.steps: List[WizardStep] = self.get_steps()

    def get_steps(self) -> List[WizardStep]:
        raise NotImplementedError

    async def on_complete(self, context: WizardContext, session) -> Any:
        """Se ejecuta al finalizar todos los pasos."""
        raise NotImplementedError

    async def process_callback(self, context: WizardContext, callback_data: str, service) -> Optional[dict]:
        """
        Process callback data from the user.
        Should return a dict with the following optional keys:
        - 'completed': bool - whether the wizard is now completed
        - 'next_step_index': int - the next step index to go to
        - 'status': str - status message for the response
        Return None if the callback isn't handled by this wizard.
        """
        # Default implementation: check current step's name and handle accordingly
        current_step = self.steps[context.current_step_index]

        # Handle VIP question callback as an example
        if current_step.name == "ask_vip":
            if callback_data in ["yes", "no"]:
                # Save the VIP information in context
                is_vip = (callback_data == "yes")
                context.data.update(vip=is_vip)

                # If VIP is yes, we need to ask for days
                # If VIP is no, we can skip the VIP days step
                if is_vip:
                    # Advance to next step to ask for VIP days
                    next_step_index = context.current_step_index + 1

                    # Render the next step which should ask for VIP days
                    if next_step_index < len(self.steps):
                        return {
                            "next_step_index": next_step_index,
                            "status": "Waiting for VIP days"
                        }
                    else:
                        # If no more steps, complete the wizard
                        return {"completed": True}
                else:
                    # If no VIP, skip to next step - we need to advance past the VIP days step
                    if context.current_step_index + 1 < len(self.steps):
                        next_step_index = context.current_step_index + 1  # Skip the VIP days step

                        # If we're now at the end (no more steps), complete the wizard
                        if next_step_index >= len(self.steps):
                            return {"completed": True}
                        else:
                            # If there are more steps after VIP days, move to the next one
                            return {
                                "next_step_index": next_step_index,
                                "status": "Moved to next step"
                            }
                    else:
                        # If there are no more steps, complete the wizard
                        return {"completed": True}
        return None