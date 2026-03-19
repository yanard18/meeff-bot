import time

from ..core.task import Task
from ..core.context import BotContext
from ..core.states import SWIPE_MODE


class SwipeTask(Task):
    """Opens profile cards on the swipe deck for evaluation.

    Purely reactive: eligible only when the Swipe Mode UI is active.
    Timer logic lives in ChatQueueTask, which preempts this task
    (priority 15 > 5) when a check interval fires.

    Priority 5.
    """

    priority = 5

    def is_eligible(self, state: str) -> bool:
        return state == SWIPE_MODE

    def run(self, ctx: BotContext, state: str) -> None:
        print("[Swipe] Tapping profile photo to open detailed view...")
        card = ctx.vision.get_node_bounds("touch_layout")
        actions = ctx.vision.get_node_bounds("action_layout")
        if card and actions:
            safe_zone = {**card, "y_max": actions["y_min"]}
            ctx.adb.human_tap(safe_zone, name="Profile Photo")
            time.sleep(ctx.config["timing"]["delay_after_opening_profile"])
        else:
            print("[Swipe] Profile card not found — skipping tick.")
