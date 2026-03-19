import os
import shutil
import time
import random

from ..engine.context import BotContext


def evaluate_and_decide(ctx: BotContext) -> None:
    """Screenshot the open detailed profile, score it, then like or nope.

    Called by any mode that encounters the Detailed Profile UI page.
    """
    t_conf = ctx.config["timing"]
    b_conf = ctx.config["behavior"]

    print("[*] Reading detailed profile...")

    photo_bounds = ctx.vision.get_node_bounds("photo_imageview")
    screenshot_path = ctx.adb.take_screenshot(crop_bounds=photo_bounds)
    time.sleep(1)

    should_like = _evaluate_profile(ctx, screenshot_path)
    _save_training_sample(screenshot_path, should_like)

    if not should_like:
        print("[*] AI scored profile below threshold. Tapping Nope...")
        nope = ctx.vision.get_node_bounds("nope_imageview")
        if nope:
            ctx.adb.human_tap(nope, name="Nope")
        time.sleep(1)
        return

    scrolls = random.choices([0, 1, 2, 3], weights=b_conf["scrolls_weights"])[0]
    for i in range(scrolls):
        print(f"[*] Executing scroll {i + 1} of {scrolls}...")
        ctx.adb.human_scroll_down()

    read_time = random.uniform(t_conf["thinking_before_like_min"], t_conf["thinking_before_like_max"])
    print(f"[*] Thinking for {read_time:.2f}s...")
    time.sleep(read_time)

    like = ctx.vision.get_node_bounds("like_imageview")
    success = ctx.adb.human_tap(like, name="Like") if like else False
    print("[+] Liked profile." if success else "[!] Failed to tap Like.")

    delay = random.uniform(t_conf["delay_after_like_min"], t_conf["delay_after_like_max"])
    print(f"[*] Waiting {delay:.2f}s...\n")
    time.sleep(delay)


def _evaluate_profile(ctx: BotContext, screenshot_path: str) -> bool:
    if not ctx.scoring_enabled:
        print("[AI] Scoring disabled. Defaulting to like.")
        return True
    return ctx.critic.evaluate(screenshot_path).liked


def _save_training_sample(screenshot_path: str, liked: bool) -> None:
    if not screenshot_path or not os.path.exists(screenshot_path):
        return
    label = "liked" if liked else "disliked"
    dest_dir = os.path.join("labeled_data", label)
    os.makedirs(dest_dir, exist_ok=True)
    ext = os.path.splitext(screenshot_path)[1] or ".jpg"
    dest = os.path.join(dest_dir, f"{int(time.time())}{ext}")
    shutil.copy(screenshot_path, dest)
    print(f"[Data] Saved training sample → {dest}")
