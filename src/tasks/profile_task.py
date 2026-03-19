import os
import shutil
import random
import time

from ..core.task import Task
from ..core.context import BotContext


class ProfileEvalTask(Task):
    """Evaluates an open detailed profile and decides like or nope.

    UI state: "ACTIVE (Detailed Profile)"
    Priority 5.
    """

    priority = 5

    def is_eligible(self, state: str) -> bool:
        return "Detailed Profile" in state

    def run(self, ctx: BotContext, state: str) -> None:
        t_conf = ctx.config["timing"]
        b_conf = ctx.config["behavior"]

        print("[Profile] Reading detailed profile...")

        photo_bounds = ctx.vision.get_node_bounds("photo_imageview")
        screenshot_path = ctx.adb.take_screenshot(crop_bounds=photo_bounds)
        time.sleep(1)

        should_like = self._evaluate(ctx, screenshot_path)
        self._save_sample(screenshot_path, should_like)

        if ctx.status:
            ctx.status.increment("profiles")

        if not should_like:
            print("[Profile] Below threshold — tapping Nope...")
            if ctx.status:
                ctx.status.increment("nopes")
            nope = ctx.vision.get_node_bounds("nope_imageview")
            if nope:
                ctx.adb.human_tap(nope, name="Nope")
            time.sleep(1)
            return

        scrolls = random.choices([0, 1, 2, 3], weights=b_conf["scrolls_weights"])[0]
        for i in range(scrolls):
            print(f"[Profile] Scroll {i + 1}/{scrolls}...")
            ctx.adb.human_scroll_down()

        think = random.uniform(t_conf["thinking_before_like_min"], t_conf["thinking_before_like_max"])
        print(f"[Profile] Thinking for {think:.2f}s...")
        time.sleep(think)

        like = ctx.vision.get_node_bounds("like_imageview")
        ok = ctx.adb.human_tap(like, name="Like") if like else False
        print("[Profile] Liked." if ok else "[Profile] Failed to tap Like.")
        if ok and ctx.status:
            ctx.status.increment("likes")

        delay = random.uniform(t_conf["delay_after_like_min"], t_conf["delay_after_like_max"])
        print(f"[Profile] Waiting {delay:.2f}s...\n")
        time.sleep(delay)

    def _evaluate(self, ctx: BotContext, screenshot_path: str) -> bool:
        if not ctx.scoring_enabled:
            print("[Profile] Scoring disabled — defaulting to like.")
            return True
        return ctx.critic.evaluate(screenshot_path).liked

    def _save_sample(self, screenshot_path: str, liked: bool) -> None:
        if not screenshot_path or not os.path.exists(screenshot_path):
            return
        label = "liked" if liked else "disliked"
        dest_dir = os.path.join("labeled_data", label)
        os.makedirs(dest_dir, exist_ok=True)
        ext = os.path.splitext(screenshot_path)[1] or ".jpg"
        dest = os.path.join(dest_dir, f"{int(time.time())}{ext}")
        shutil.copy(screenshot_path, dest)
        print(f"[Profile] Saved training sample → {dest}")
