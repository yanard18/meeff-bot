import time

from ..core.task import Task
from ..core.context import BotContext


class ChatListTask(Task):
    """Processes the chat list: matched friends first, then incoming likes.

    UI state: "ACTIVE (Chat List)"
    Priority 10 — runs before swipe/profile tasks since matched friends expire.
    """

    priority = 10

    def is_eligible(self, state: str) -> bool:
        return "Chat List" in state

    def run(self, ctx: BotContext, state: str) -> None:
        count = ctx.vision.get_matched_friends_count()
        if count > 0:
            print(f"[ChatList] {count} matched friend(s) — opening first...")
            first = ctx.vision.get_first_matched_friend_bounds()
            if first:
                ctx.adb.human_tap(first, name="Matched Friend")
                time.sleep(1.5)
                return
            print("[ChatList] Thumbnail not found — skipping matches.")

        like_tab = ctx.vision.get_like_inner_tab_bounds()
        if like_tab:
            print("[ChatList] Navigating to Like tab...")
            ctx.adb.human_tap(like_tab, name="Like Tab")
            time.sleep(1.5)
        else:
            print("[ChatList] Nothing to process — returning to swipe.")
            tab = ctx.vision.get_node_bounds("tab_explore")
            if tab:
                ctx.adb.human_tap(tab, name="Swipe Tab")
                time.sleep(1.5)
