import time

from ...engine.mode import Mode
from ...engine.context import BotContext


class ChatListState(Mode):
    """Handles the chat list: processes matched friends first, then navigates to likes.

    UI: ACTIVE (Chat List)
    """

    @property
    def name(self) -> str:
        return "Chat List"

    def execute(self, ctx: BotContext) -> None:
        count = ctx.vision.get_matched_friends_count()
        if count > 0:
            print(f"[Chat] {count} matched friend(s) — opening first...")
            first = ctx.vision.get_first_matched_friend_bounds()
            if first:
                ctx.adb.human_tap(first, name="Matched Friend")
                time.sleep(1.5)
                return
            print("[Chat] Thumbnail not found — skipping matches.")

        like_tab = ctx.vision.get_like_inner_tab_bounds()
        if like_tab:
            ctx.adb.human_tap(like_tab, name="Like Tab")
            time.sleep(1.5)
        else:
            print("[Chat] Nothing to process — returning to swipe.")
            tab = ctx.vision.get_node_bounds("tab_explore")
            if tab:
                ctx.adb.human_tap(tab, name="Swipe Tab")
                time.sleep(1.5)
