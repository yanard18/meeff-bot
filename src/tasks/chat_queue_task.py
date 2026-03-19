import time

from ..core.task import Task
from ..core.context import BotContext
from ..core.platform import ChatCandidate
from ..core.scheduler import PeriodicScheduler


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

    Flow each tick (while "Chat List" is on screen):
      1. If this is a new session: reset scheduler timers, discover candidates,
         build the priority queue.
      2. If session has timed out: finish and navigate to likes.
      3. If queue is non-empty: pop the top candidate and tap to open it.
         ChatTask (priority 50) handles the conversation; when it presses back,
         state returns to "Chat List" and we run again for the next candidate.
      4. If queue is empty after working through it: finish → likes page.

    LikePageTask (priority 10) handles the likes page once we navigate there.

    Priority 15 — above ChatListTask (10) so it controls the chat list page.
    """

    priority = 15

    def __init__(
        self,
        scheduler: PeriodicScheduler,
        matches_interval: float,
        likes_interval: float,
        chat_interval: float,
        max_session_seconds: float = 600,
    ) -> None:
        self._scheduler = scheduler
        self._matches_interval = matches_interval
        self._likes_interval = likes_interval
        self._chat_interval = chat_interval
        self._max_session = max_session_seconds
        self._queue: list[ChatCandidate] = []
        self._mode_started: float | None = None

    # ------------------------------------------------------------------
    # Task interface
    # ------------------------------------------------------------------

    def is_eligible(self, state: str) -> bool:
        return "Chat List" in state or self._chat_timer_due()

    def needs_navigation(self, state: str) -> bool:
        return self._chat_timer_due() and "Chat List" not in state

    def navigate_to(self, ctx: BotContext) -> None:
        print("[ChatQueue] Chat timer fired — navigating to chat list...")
        self._scheduler.reset("chat_queue")
        ctx.platform.navigate_to_chat_list()

    def cancel_navigation(self, ctx: BotContext) -> None:
        print("[ChatQueue] Navigation blocked — resetting chat timer, will retry later.")
        self._scheduler.reset("chat_queue")

    def run(self, ctx: BotContext, state: str) -> None:
        # Session timeout guard
        if self._mode_started and time.time() - self._mode_started > self._max_session:
            print("[ChatQueue] Session timeout — moving to likes.")
            self._finish(ctx)
            return

        if not self._queue:
            # New session starting: reset any due timers then discover candidates
            self._reset_due_timers()
            candidates = ctx.platform.get_chat_candidates()
            if not candidates:
                print("[ChatQueue] No chat candidates — moving to likes.")
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

    def _chat_timer_due(self) -> bool:
        return self._scheduler.is_due("chat_queue", self._chat_interval)

    def _reset_due_timers(self) -> None:
        if self._scheduler.is_due("matches", self._matches_interval):
            self._scheduler.reset("matches")
        if self._scheduler.is_due("likes", self._likes_interval):
            self._scheduler.reset("likes")
        if self._chat_timer_due():
            self._scheduler.reset("chat_queue")
