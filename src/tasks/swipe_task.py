import time

from ..core.task import Task
from ..core.context import BotContext
from ..core.scheduler import PeriodicScheduler


class SwipeTask(Task):
    """Handles the swipe deck: opens profiles or navigates to chat on a timer.

    UI state: "ACTIVE (Swipe Mode)"
    Priority 5.
    """

    priority = 5

    def __init__(self, scheduler: PeriodicScheduler) -> None:
        self._scheduler = scheduler

    def is_eligible(self, state: str) -> bool:
        return "Swipe Mode" in state

    def run(self, ctx: BotContext, state: str) -> None:
        interval_matches = ctx.config.get("matched_check_interval_minutes", 5) * 60
        interval_likes = ctx.config.get("likes_check_interval_minutes", 10) * 60

        if (self._scheduler.is_due("matches", interval_matches)
                or self._scheduler.is_due("likes", interval_likes)):
            self._scheduler.reset("matches")
            self._scheduler.reset("likes")
            print("[Swipe] Periodic check — navigating to chat list...")
            ctx.platform.navigate_to_chat_list()
        else:
            self._open_profile(ctx)

    def _open_profile(self, ctx: BotContext) -> None:
        print("[Swipe] Tapping profile photo to open detailed view...")
        card    = ctx.vision.get_node_bounds("touch_layout")
        actions = ctx.vision.get_node_bounds("action_layout")
        if card and actions:
            safe_zone = {**card, "y_max": actions["y_min"]}
            ctx.adb.human_tap(safe_zone, name="Profile Photo")
            time.sleep(ctx.config["timing"]["delay_after_opening_profile"])
        else:
            print("[Swipe] Profile card not found — skipping tick.")
