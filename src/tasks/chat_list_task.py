import time

from ..core.task import Task
from ..core.context import BotContext
from ..core.scheduler import PeriodicScheduler


class ChatListTask(Task):
    """Scheduled task: checks matched friends and incoming likes on a timer.

    is_eligible() fires when a timer is due (regardless of current UI) OR
    when the bot is already on the chat list page (to handle accidental
    landings — e.g. ChatTask pressing back — by returning to swipe).

    needs_navigation() returns True only when a timer has fired but the bot
    is not yet on the chat list page; the Orchestrator will call navigate_to()
    and defer run() to the next tick.

    Priority 10 — preempts SwipeTask (5) when the timer fires.
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
        return self._timer_due() or "Chat List" in state

    def needs_navigation(self, state: str) -> bool:
        # Only navigate when a timer fired and we're on the wrong page.
        return self._timer_due() and "Chat List" not in state

    def navigate_to(self, ctx: BotContext) -> None:
        print("[ChatList] Timer fired — navigating to chat list...")
        ctx.platform.navigate_to_chat_list()

    def run(self, ctx: BotContext, state: str) -> None:
        if not self._timer_due():
            # Landed here by accident (e.g. ChatTask pressed back).
            print("[ChatList] No timer due — returning to swipe.")
            ctx.platform.navigate_to_swipe()
            return

        # Reset only the timers that actually fired.
        if self._scheduler.is_due("matches", self._matches_interval):
            self._scheduler.reset("matches")
        if self._scheduler.is_due("likes", self._likes_interval):
            self._scheduler.reset("likes")

        friends = ctx.platform.get_matched_friends()
        if friends:
            print(f"[ChatList] {len(friends)} matched friend(s) — opening first...")
            ctx.adb.human_tap(friends[0].bounds, name="Matched Friend")
            time.sleep(1.5)
            return

        print("[ChatList] No matched friends — navigating to likes...")
        ctx.platform.navigate_to_likes()

        if "Like" not in ctx.platform.detect_state():
            print("[ChatList] Likes tab not found — returning to swipe.")
            ctx.platform.navigate_to_swipe()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _timer_due(self) -> bool:
        return (
            self._scheduler.is_due("matches", self._matches_interval)
            or self._scheduler.is_due("likes", self._likes_interval)
        )
