from abc import ABC, abstractmethod
from .context import BotContext


class Mode(ABC):
    """Base class for FSM states.

    Each subclass handles exactly one UI page. The FSMEngine detects the
    current UI string each tick and transitions to the first registered Mode
    whose matches() returns True.

    Subclasses must define:
        name         — unique string identifier
        execute(ctx) — called every tick while this state is active

    Optionally override:
        matches(ui_string) — custom matching logic (default: name in ui_string)
        on_enter(ctx)      — called once when transitioning into this state
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    def matches(self, ui_string: str) -> bool:
        return self.name in ui_string

    def on_enter(self, ctx: BotContext) -> None:
        pass

    @abstractmethod
    def execute(self, ctx: BotContext) -> None: ...
