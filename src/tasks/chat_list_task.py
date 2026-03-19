from ..core.task import Task
from ..core.context import BotContext
from ..core.scheduler import PeriodicScheduler


class ChatListTask(Task):
    """Navigates to the chat list when a periodic timer fires.

    Responsibility: timer ownership + navigation only.
    Everything that happens on the chat list page is handled by
    ChatQueueTask (priority 15), which takes over on the next tick.

    needs_navigation() fires when the timer is due and we are on the wrong
    page. navigate_to() resets the timers immediately so that ChatQueueTask
    does not see them as still-due when it runs.

    Priority 10.
    """

    priority = 10

    def __init__(
        self,
        scheduler: PeriodicScheduler,
        matches_interval: float,
        likes_interval: float,
    ) -> None:
        self._scheduler = scheduler
        self._matches_interval = matches_interval
        self._likes_interval = likes_interval

    # ------------------------------------------------------------------
    # Task interface
    # ------------------------------------------------------------------

    def is_eligible(self, state: str) -> bool:
        return self._timer_due()

    def needs_navigation(self, state: str) -> bool:
        return self._timer_due() and "Chat List" not in state

    def navigate_to(self, ctx: BotContext) -> None:
        print("[ChatList] Timer fired — navigating to chat list...")
        self._reset_due_timers()
        ctx.platform.navigate_to_chat_list()

    def cancel_navigation(self, ctx: BotContext) -> None:
        print("[ChatList] Navigation blocked — resetting timers, will retry later.")
        self._reset_due_timers()

    def run(self, ctx: BotContext, state: str) -> None:
        # Timer fired and we are already on the chat list (no navigation needed).
        # Reset timers so ChatQueueTask does not see them as due.
        self._reset_due_timers()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _timer_due(self) -> bool:
        return (
            self._scheduler.is_due("matches", self._matches_interval)
            or self._scheduler.is_due("likes", self._likes_interval)
        )

    def _reset_due_timers(self) -> None:
        if self._scheduler.is_due("matches", self._matches_interval):
            self._scheduler.reset("matches")
        if self._scheduler.is_due("likes", self._likes_interval):
            self._scheduler.reset("likes")
