import time

from ..core.task import Task
from ..core.context import BotContext

_DIALOG_STATES = {
    "ACTIVE (Ad)",
    "ACTIVE (Native Ad)",
    "ACTIVE (Match Complete)",
    "ACTIVE (Suggest Meeff)",
    "ACTIVE (Quit Dialog)",
}


class DialogTask(Task):
    """Dismisses any blocking dialog or ad overlay.

    Priority 100 — always runs before any content task so dialogs never
    accumulate and jam the bot.
    """

    priority = 100

    def is_eligible(self, state: str) -> bool:
        return state in _DIALOG_STATES

    def run(self, ctx: BotContext, state: str) -> None:
        if state == "ACTIVE (Ad)":
            print("[Dialog] WebView ad — closing via close button...")
            bounds = (ctx.vision.get_node_bounds_by_desc("Close ad")
                      or ctx.vision.get_node_bounds_by_desc("Ad closed"))
            if bounds:
                ctx.adb.human_tap(bounds, margin=10, name="Ad Close")
            else:
                ctx.adb.press_back()

        elif state == "ACTIVE (Native Ad)":
            print("[Dialog] Native ad — pressing back...")
            ctx.adb.press_back()

        elif state == "ACTIVE (Match Complete)":
            print("[Dialog] Match complete — dismissing...")
            bounds = ctx.vision.get_node_bounds("top_left_imageview")
            if bounds:
                ctx.adb.human_tap(bounds, name="Close Match")
            else:
                ctx.adb.press_back()

        elif state == "ACTIVE (Suggest Meeff)":
            print("[Dialog] Suggest Meeff dialog — dismissing...")
            bounds = ctx.vision.get_node_bounds("close_textview")
            if bounds:
                ctx.adb.human_tap(bounds, name="Next time")
            else:
                ctx.adb.press_back()

        elif state == "ACTIVE (Quit Dialog)":
            print("[Dialog] Quit dialog — tapping Cancel...")
            bounds = ctx.vision.get_node_bounds("negativeButton")
            if bounds:
                ctx.adb.human_tap(bounds, name="Cancel")
            else:
                ctx.adb.press_back()

        time.sleep(2)
