# Wizard Engine

## Overview

The Wizard Engine is a flexible system for creating guided, multi-step interactions with users. It's designed to handle complex forms and workflows in a conversational manner, allowing users to input data step-by-step with validation and conditional logic.

## Architecture

The Wizard Engine follows a 3-layer architecture:

### 1. Core Layer (`bot/wizards/core.py`)
- **WizardContext**: Dataclass that maintains the state of an active wizard session, including current step, collected data, and return context for nested flows
- **WizardStep**: Dataclass that defines a single step in the wizard, including text provider, keyboard provider, validator, and processing callback
- **BaseWizard**: Abstract base class that defines the structure and behavior of a wizard

### 2. Service Layer (`bot/services/wizard_service.py`)
- **WizardService**: Central orchestration service that manages active wizard sessions, processes user input, handles validation, and manages state transitions
- Handles both message and callback query inputs
- Manages wizard lifecycle (start, progress, completion)
- Integrates with the FSM context for state persistence

### 3. Presentation Layer (`bot/handlers/wizard_handler.py`)
- **handle_wizard_message**: Processes text input during active wizard sessions
- **handle_wizard_callback**: Processes inline keyboard callbacks during active wizard sessions
- Generic handlers that work with any wizard implementation

## Core Components

### WizardContext
```python
@dataclass
class WizardContext:
    wizard_id: str                    # Unique identifier for the wizard type
    current_step_index: int = 0      # Current step in the wizard flow
    data: dict = field(default_factory=dict)  # Collected user data
    return_context: Optional[dict] = None     # Context for nested flows
```

### WizardStep
```python
@dataclass
class WizardStep:
    name: str                        # Step identifier
    text_provider: Callable[[WizardContext], str]  # Function to generate step text
    keyboard_provider: Optional[Callable[[WizardContext], InlineKeyboardMarkup]] = None
    validator: Optional[Callable[[Any], Union[Any, None]]] = None  # Validation function
    on_valid: Optional[Callable[[WizardContext, Any], None]] = None  # Data processing callback
```

### BaseWizard
```python
class BaseWizard:
    def get_steps(self) -> List[WizardStep]:  # Define the steps
    async def on_complete(self, context: WizardContext, session) -> Any:  # Final processing
```

## Available Wizards

### RankWizard (`bot/wizards/rank_wizard.py`)
A wizard for creating new gamification ranks with the following flow:
1. **rank_name**: Ask for the rank name (min 3 characters)
2. **rank_points**: Ask for required points (integer validation)
3. **ask_vip**: Yes/No question about VIP rewards (with inline keyboard)
4. **vip_days**: If VIP is enabled, ask for number of days (integer validation)

The wizard creates a new rank in the database with the specified parameters when completed.

## Common Validators (`bot/wizards/validators.py`)
- `text_min_length(min_len)`: Validates minimum text length
- `is_integer(min_val)`: Validates integer input with minimum value
- Additional business logic validators can be injected

## UI Renderer (`bot/wizards/ui_renderer.py`)
- `yes_no_keyboard()`: Creates a simple yes/no inline keyboard for wizard steps

## Integration with the System

### Starting a Wizard
Wizards are typically started from other handlers (e.g., admin menu) using the `WizardService.start_wizard()` method:

```python
await wizard_service.start_wizard(
    user_id=callback_query.from_user.id,
    wizard_class=RankWizard,
    fsm_context=state,
    services=services  # Pass services for use in completion
)
```

### State Management
- Active wizards are tracked in `WizardService.active_wizards`
- FSM state is set to "wizard_active" to route messages to wizard handlers
- Wizard context is stored in FSM data for persistence

### Completion Handling
When a wizard completes successfully:
1. The `on_complete` method is called to process final data
2. The wizard context is removed from active wizards
3. FSM state is cleared
4. Success message is sent to the user

## Error Handling
- Invalid input triggers re-rendering of the current step with error message
- Validation failures provide user feedback
- Missing active wizard sessions are handled gracefully
- Database operations are managed within the existing session context

## Usage Examples

### Creating a New Wizard
To create a new wizard, extend the `BaseWizard` class:

```python
from bot.wizards.core import BaseWizard, WizardStep, WizardContext
from bot.wizards.validators import CommonValidators
from typing import List

class MyNewWizard(BaseWizard):
    def get_steps(self) -> List[WizardStep]:
        return [
            WizardStep(
                name="step_name",
                text_provider=lambda ctx: "What is your name?",
                validator=CommonValidators.text_min_length(2),
                on_valid=lambda ctx, val: ctx.data.update(name=val)
            ),
            # Add more steps as needed
        ]

    async def on_complete(self, context: WizardContext, session):
        # Process the collected data
        # Return result or perform final operations
        pass
```

### Starting the Wizard
```python
from bot.services.wizard_service import WizardService
from my_new_wizard import MyNewWizard

wizard_service = WizardService()
await wizard_service.start_wizard(
    user_id=user_id,
    wizard_class=MyNewWizard,
    fsm_context=state,
    services=services
)
```

## Benefits

- **Modular Design**: Easy to create new wizards without duplicating code
- **Validation**: Built-in validation system with custom validators
- **Conditional Logic**: Support for conditional steps based on user input
- **State Management**: Proper state persistence using FSM
- **Reusability**: Generic handlers work with any wizard implementation
- **Integration**: Seamlessly integrates with existing service container and database session patterns