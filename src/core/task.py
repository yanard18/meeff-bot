from abc import ABC, abstractmethod

from .context import BotContext


class Task(ABC):
    """Base class for all bot tasks.

    Each subclass handles exactly one logical activity (swiping, chatting,
    processing likes, …). The Orchestrator detects the current UI state once
    per tick, then asks each registered task (in priority order) whether it is
    eligible to run.

    Subclasses must define:
        priority        — int; higher = runs first when multiple tasks match
        is_eligible()   — returns True when this task should handle the state
        run()           — executes one unit of work
    """

    priority: int = 0

    @abstractmethod
    def is_eligible(self, state: str) -> bool:
        """Return True if this task should handle the given UI state string."""

    @abstractmethod
    def run(self, ctx: BotContext, state: str) -> None:
        """Execute one unit of work for the current state.

        `state` is the same string that was passed to is_eligible(), provided
        again so tasks don't need to re-detect the UI.
        """
