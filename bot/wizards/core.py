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