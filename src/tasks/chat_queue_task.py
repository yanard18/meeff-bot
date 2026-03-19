import time

from ..core.task import Task
from ..core.context import BotContext
from ..core.platform import ChatCandidate
from ..core.scheduler import PeriodicScheduler
from ..core.states import CHAT_LIST


def _prioritize(candidates: list[ChatCandidate]) -> list[ChatCandidate]:
    """Score and sort candidates. Higher score = open first.

    Scoring:
      +2  is_matched  — expires soon, must act
      +1  has_unread  — they messaged us, high engagement
    """
    for c in candidates:
        c.score = (2.0 if c.is_matched else 0.0) + (1.0 if c.has_unread else 0.0)
    return sorted(candidates, key=lambda c: c.score, reverse=True)


class ChatQueueTask(Task):
    """Works through a prioritized queue of chat candidates on the Chat List page.

    Owns two periodic timers: chat_queue (general inbox check) and likes
    (incoming likes page). Matched friends are discovered as part of the normal
    chat_queue pass — no separate matches timer is needed.

    Triggers navigation when any timer fires and we are not on the chat list.
    Once on the chat list:
      1. New session: reset due timers, discover & prioritize candidates.
      2. Session timeout: finish → navigate to swipe.
      3. Queue non-empty: pop top candidate and tap to open.
         ChatTask (priority 50) handles the conversation; when it presses back,
         state returns to CHAT_LIST and this task runs again.
      4. Queue empty: finish → navigate to swipe.

    Priority 15.
    """

    priority = 15

    def __init__(
        self,
        scheduler: PeriodicScheduler,
        likes_interval: float,
        chat_interval: float,
        max_session_seconds: float = 600,
    ) -> None:
        self._scheduler = scheduler
        self._likes_interval = likes_interval
        self._chat_interval = chat_interval
        self._max_session = max_session_seconds
        self._queue: list[ChatCandidate] = []
        self._mode_started: float | None = None

    # ------------------------------------------------------------------
    # Task interface
    # ------------------------------------------------------------------

    def is_eligible(self, state: str) -> bool:
        return state == CHAT_LIST or self._any_timer_due()

    def needs_navigation(self, state: str) -> bool:
        return self._any_timer_due() and state != CHAT_LIST

    def navigate_to(self, ctx: BotContext) -> None:
        print("[ChatQueue] Timer fired — navigating to chat list...")
        self._reset_due_timers()
        ctx.platform.navigate_to_chat_list()

    def cancel_navigation(self, ctx: BotContext) -> None:
        print("[ChatQueue] Navigation blocked — resetting timers, will retry later.")
        self._reset_due_timers()

    def run(self, ctx: BotContext, state: str) -> None:
        # Session timeout guard
        if self._mode_started and time.time() - self._mode_started > self._max_session:
            print("[ChatQueue] Session timeout — moving to swipe.")
            self._finish(ctx)
            return

        if not self._queue:
            # New session: reset any due timers then discover candidates
            self._reset_due_timers()
            candidates = ctx.platform.get_chat_candidates()
            if not candidates:
                print("[ChatQueue] No chat candidates — moving to swipe.")
                self._finish(ctx)
                return
            self._queue = _prioritize(candidates)
            self._mode_started = time.time()
            print(f"[ChatQueue] Session started — {len(self._queue)} candidate(s) queued.")

        candidate = self._queue.pop(0)
        print(f"[ChatQueue] Opening chat with {candidate.name}...")
        ctx.adb.human_tap(candidate.bounds, name=f"Chat: {candidate.name}")
        time.sleep(1.5)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _finish(self, ctx: BotContext) -> None:
        self._queue.clear()
        self._mode_started = None
        ctx.platform.navigate_to_swipe()

    def _any_timer_due(self) -> bool:
        return (
            self._scheduler.is_due("chat_queue", self._chat_interval)
            or self._scheduler.is_due("likes", self._likes_interval)
        )

    def _reset_due_timers(self) -> None:
        for key, interval in (
            ("chat_queue", self._chat_interval),
            ("likes", self._likes_interval),
        ):
            if self._scheduler.is_due(key, interval):
                self._scheduler.reset(key)
