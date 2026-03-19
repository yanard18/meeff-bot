import time

from ...engine.mode import Mode
from ...engine.context import BotContext


class LikePageState(Mode):
    """Opens liked profiles one by one; returns to swipe when done.

    UI: ACTIVE (Like/Visitor Page)
    """

    @property
    def name(self) -> str:
        return "Like/Visitor Page"

    def execute(self, ctx: BotContext) -> None:
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
