from abc import ABC, abstractmethod

from .context import BotContext


class Task(ABC):
    """Base class for all bot tasks.

    Tasks are either *reactive* or *scheduled*:

    Reactive tasks (DialogTask, ChatTask, ProfileEvalTask):
        is_eligible() returns True when the right UI is on screen.
        needs_navigation() always returns False (default).

    Scheduled tasks (ChatQueueTask):
        is_eligible() returns True when a timer has fired, regardless of
        the current UI.
        needs_navigation() returns True when the timer fired but the bot is
        on the wrong page.
        navigate_to() performs the navigation; run() is called next tick.

    The Orchestrator calls needs_navigation() before run() and will navigate
    instead of running when it returns True, so tasks never need to assume
    they are already on the correct page.

    Subclasses must define:
        priority      — int; higher = runs first when multiple tasks match
        is_eligible() — returns True when this task should run
        run()         — executes one unit of work
    """

    priority: int = 0

    @abstractmethod
    def is_eligible(self, state: str) -> bool:
        """Return True if this task should handle the given UI state string."""

    def needs_navigation(self, state: str) -> bool:
        """Return True if this task is eligible but the current UI is wrong.

        When True the Orchestrator calls navigate_to() this tick and defers
        run() to the next tick (by which time the UI should have changed).
        Default: False — reactive tasks never need navigation.
        """
        return False

    def navigate_to(self, ctx: BotContext) -> None:
        """Navigate to this task's required page.

        Only called when needs_navigation() returns True.
        Default: no-op.
        """

    def cancel_navigation(self, ctx: BotContext) -> None:
        """Called by the Orchestrator when repeated navigation attempts have
        all failed (state did not change after nav_failure_threshold ticks).

        Override to reset timers, press back, or take any corrective action.
        Default: no-op.
        """

    @abstractmethod
    def run(self, ctx: BotContext, state: str) -> None:
        """Execute one unit of work for the current state.

        `state` is the same string that was passed to is_eligible(), provided
        again so tasks don't need to re-detect the UI.
        """
