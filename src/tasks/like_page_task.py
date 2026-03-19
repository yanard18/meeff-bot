import time

from ..core.task import Task
from ..core.context import BotContext


class LikePageTask(Task):
    """Opens liked profiles one by one; returns to swipe when the queue is empty.

    UI state: "ACTIVE (Like/Visitor Page)"
    Priority 10.
    """

    priority = 10

    def is_eligible(self, state: str) -> bool:
        return "Like/Visitor Page" in state

    def run(self, ctx: BotContext, state: str) -> None:
        count = ctx.vision.get_like_count()
        print(f"[Likes] {count} incoming like(s) pending.")

        if count > 0:
            profile = ctx.vision.get_first_liked_profile_bounds()
            if profile:
                ctx.adb.human_tap(profile, name="Liked Profile")
                time.sleep(ctx.config["timing"]["delay_after_opening_profile"])
                return
            print("[Likes] Thumbnail not found — returning to swipe.")
        else:
            print("[Likes] No more incoming likes — returning to swipe.")

        tab = ctx.vision.get_node_bounds("tab_explore")
        if tab:
            ctx.adb.human_tap(tab, name="Swipe Tab")
            time.sleep(1.5)
