#!/usr/bin/env python3
import os
import subprocess
import time

from dotenv import load_dotenv
load_dotenv()


EMULATOR_BIN = os.path.expanduser("~/android-sdk/emulator/emulator")
ADB_BIN      = os.path.expanduser("~/android-sdk/platform-tools/adb")
AVD_NAME     = "meeff_bot"


def is_emulator_running():
    """Returns True if an Android emulator is already listed by adb."""
    try:
        result = subprocess.run(
            [ADB_BIN, "devices"],
            capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.strip().splitlines()[1:]  # skip header
        return any("emulator" in line and "device" in line for line in lines)
    except Exception:
        return False


def start_emulator():
    """Launches the emulator in the background and waits until adb sees it."""
    print(f"[Emulator] Starting AVD '{AVD_NAME}'...")
    subprocess.Popen(
        [EMULATOR_BIN, "-avd", AVD_NAME, "-gpu", "host",
         "-memory", "4096", "-no-metrics"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True   # detach so it survives if this shell closes
    )

    print("[Emulator] Waiting for device to come online", end="", flush=True)
    for _ in range(60):          # up to 2 minutes
        time.sleep(2)
        print(".", end="", flush=True)
        if is_emulator_running():
            print(" ready!")
            subprocess.run(
                [ADB_BIN, "wait-for-device", "shell",
                 "while [[ -z $(getprop sys.boot_completed) ]]; do sleep 2; done"],
                timeout=120, capture_output=True
            )
            print("[Emulator] Boot completed.")
            return

    print("\n[Emulator] Timed out waiting for emulator. Proceeding anyway...")


def build_bot():
    """Wire up all services, platform, and tasks; return a ready Orchestrator."""
    from src.adb_service import AdbService
    from src.vision_service import VisionService
    from src.ai_service import AIService
    from clip_critic import ClipCritic

    from src.core.context import BotContext
    from src.core.scheduler import PeriodicScheduler
    from src.core.orchestrator import Orchestrator
    from src.core.status_bar import StatusBar

    from src.platforms.meeff import MeeffPlatform

    from src.tasks.dialog_task import DialogTask
    from src.tasks.chat_task import ChatTask
    from src.tasks.chat_list_task import ChatListTask
    from src.tasks.like_page_task import LikePageTask
    from src.tasks.profile_task import ProfileEvalTask
    from src.tasks.swipe_task import SwipeTask
    from src.tasks.recovery_task import RecoveryTask

    # Services
    adb = AdbService()
    vision = VisionService(adb)
    config = adb.config

    ai_conf = config.get("ai", {})
    ai = AIService(ai_conf)
    scoring_enabled = ai_conf.get("enabled", False)
    clip_threshold = ai_conf.get("clip_threshold", 0.6)
    critic = ClipCritic(threshold=clip_threshold)

    print(f"[Bot] CLIP threshold={clip_threshold} | scoring={'on' if scoring_enabled else 'off'}")

    # Platform adapter
    platform = MeeffPlatform(adb, vision)

    # Scheduler + status bar (must exist before BotContext)
    scheduler = PeriodicScheduler()
    likes_interval = config.get("likes_check_interval_minutes", 10) * 60
    matched_interval = config.get("matched_check_interval_minutes", 5) * 60

    # Prime both timers so the first check fires after the configured interval,
    # not immediately on startup (scheduler._last defaults to epoch 0).
    scheduler.reset("likes")
    scheduler.reset("matches")

    status = StatusBar(scheduler)
    status.register_timer("Likes check", "likes", likes_interval)
    status.register_timer("Matched check", "matches", matched_interval)

    ctx = BotContext(
        adb=adb,
        vision=vision,
        ai=ai,
        critic=critic,
        config=config,
        platform=platform,
        scoring_enabled=scoring_enabled,
        status=status,
    )

    # Task registry — Orchestrator sorts by priority automatically
    tasks = [
        DialogTask(),           # priority 100 — dialogs always first
        ChatTask(),             # priority  50 — hold chat until decided to leave
        ChatListTask(),         # priority  10 — matched friends expire!
        LikePageTask(),         # priority  10
        ProfileEvalTask(),      # priority   5
        SwipeTask(scheduler),   # priority   5
        RecoveryTask(),         # priority   1 — fallback
    ]

    return Orchestrator(ctx, tasks)


if __name__ == '__main__':
    if not is_emulator_running():
        start_emulator()
    else:
        print("[Emulator] Already running.")

    bot = build_bot()
    bot.run()
