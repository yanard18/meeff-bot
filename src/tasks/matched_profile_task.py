import time

from ..core.task import Task
from ..core.context import BotContext


class MatchedProfileTask(Task):
    """Handles the matched-friend profile page shown after tapping a match card.

    UI state: "ACTIVE (Matched Friend Profile)"
    Unique fingerprint: open_chat_layout resource-id.

    This page is an intermediate screen — it shows the match's profile photo,
    name, age, bio, and a 'Send a message to <name>' button. The task:
      1. Harvests all available profile data (photo, name, age, bio).
      2. Taps open_chat_layout to enter the actual chat.
         ChatTask (priority 50) then handles the conversation.

    Priority 60 — above ChatTask so it runs first on this intermediate page,
    transitions into the chat, and then steps aside.
    """

    priority = 60

    def is_eligible(self, state: str) -> bool:
        return "Matched Friend Profile" in state

    def run(self, ctx: BotContext, state: str) -> None:
        print("[MatchedProfile] Harvesting profile data...")

        photo_bounds = ctx.vision.get_node_bounds("photo_imageview")
        screenshot_path = ctx.adb.take_screenshot(crop_bounds=photo_bounds)

        if ctx.harvest:
            ctx.harvest.harvest_profile(screenshot_path=screenshot_path)

        chat_button = ctx.vision.get_node_bounds("open_chat_layout")
        if chat_button:
            print("[MatchedProfile] Tapping 'Send a message' button...")
            ctx.adb.human_tap(chat_button, name="Open Chat")
            time.sleep(1.5)
        else:
            print("[MatchedProfile] Chat button not found — pressing back.")
            ctx.adb.press_back()
            time.sleep(1)
