import time

from ..core.task import Task
from ..core.context import BotContext
from ..core.states import LIKE_VISITOR_PAGE


class LikePageTask(Task):
    """Opens liked profiles one by one; returns to swipe when the queue is empty.

    UI state: "ACTIVE (Like/Visitor Page)"
    Priority 10.
    """

    priority = 10

    def is_eligible(self, state: str) -> bool:
        return state == LIKE_VISITOR_PAGE

    def run(self, ctx: BotContext, state: str) -> None:
        profiles = ctx.platform.get_liked_profiles()

        if profiles:
            print(f"[Likes] {len(profiles)} incoming like(s) pending.")
            ctx.adb.human_tap(profiles[0].bounds, name="Liked Profile")
            time.sleep(ctx.config["timing"]["delay_after_opening_profile"])
            return

        print("[Likes] No more incoming likes — returning to swipe.")
        ctx.platform.navigate_to_swipe()
