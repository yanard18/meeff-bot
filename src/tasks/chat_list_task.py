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
        friends = ctx.platform.get_matched_friends()
        if friends:
            print(f"[ChatList] {len(friends)} matched friend(s) — opening first...")
            ctx.adb.human_tap(friends[0].bounds, name="Matched Friend")
            time.sleep(1.5)
            return

        print("[ChatList] No matched friends — navigating to likes...")
        ctx.platform.navigate_to_likes()

        # If navigate_to_likes found nothing, fall back to swipe.
        if "Like" not in ctx.platform.detect_state():
            print("[ChatList] Likes tab not found — returning to swipe.")
            ctx.platform.navigate_to_swipe()
