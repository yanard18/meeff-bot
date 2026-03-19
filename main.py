#!/usr/bin/env python3
from dotenv import load_dotenv
load_dotenv()

from src import emulator


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

    from profile_db import ProfileStore, HarvestService

    from src.core.message_generator import AIMessageGenerator

    from src.tasks.dialog_task import DialogTask
    from src.tasks.matched_profile_task import MatchedProfileTask
    from src.tasks.chat_task import ChatTask
    from src.tasks.chat_queue_task import ChatQueueTask
    from src.tasks.like_page_task import LikePageTask
    from src.tasks.profile_task import ProfileEvalTask
    from src.tasks.swipe_task import SwipeTask
    from src.tasks.recovery_task import RecoveryTask
    from src.tasks.sleep_task import SleepTask
    from src.tasks.switch_region_task import SwitchRegionTask

    # Services
    adb = AdbService()
    vision = VisionService(adb)
    config = adb.config

    store = ProfileStore("data/profiles.db")
    harvest = HarvestService(store=store, vision=vision, adb=adb, platform="meeff")

    ai_conf = config.get("ai", {})
    ai = AIService(ai_conf)
    clip_enabled = ai_conf.get("clip_enabled", ai_conf.get("enabled", False))
    chat_enabled = ai_conf.get("chat_enabled", ai_conf.get("enabled", False))
    clip_threshold = ai_conf.get("clip_threshold", 0.6)
    critic = ClipCritic(threshold=clip_threshold)

    persona_config = config.get("chat_persona", {})
    message_generator = AIMessageGenerator(ai, persona_config) if persona_config else None

    print(f"[Bot] CLIP threshold={clip_threshold} | clip={'on' if clip_enabled else 'off'} | chat={'on' if chat_enabled else 'off'}")

    # Platform adapter
    platform = MeeffPlatform(adb, vision)

    # Task enable flags — resolved early so timer setup can use them too.
    task_conf = config.get("tasks", {})
    def _on(name: str) -> bool:
        return task_conf.get(name, True)

    # Scheduler + status bar (must exist before BotContext)
    scheduler = PeriodicScheduler()
    likes_interval  = config.get("likes_check_interval_minutes", 10) * 60
    chat_interval   = config.get("chat_queue_interval_minutes", 5) * 60
    sleep_interval  = config.get("sleep_interval_minutes", 30) * 60
    sleep_duration  = config.get("sleep_duration_minutes", 20) * 60
    region_conf     = config.get("region_rotation", {})
    region_interval = region_conf.get("interval_minutes", 8) * 60
    region_nations  = region_conf.get("nationalities", [])

    status = StatusBar(scheduler)

    # Only prime and register timers for enabled tasks.
    if _on("chat_queue"):
        scheduler.reset("likes")
        scheduler.reset("chat_queue")
        status.register_timer("Likes check", "likes",     likes_interval)
        status.register_timer("Chat queue",  "chat_queue", chat_interval)
    if _on("sleep"):
        scheduler.reset("sleep")
        status.register_timer("Sleep", "sleep", sleep_interval)
    if _on("switch_region"):
        scheduler.reset("switch_region")
        status.register_timer("Region switch", "switch_region", region_interval)

    ctx = BotContext(
        adb=adb,
        vision=vision,
        ai=ai,
        critic=critic,
        config=config,
        platform=platform,
        clip_enabled=clip_enabled,
        chat_enabled=chat_enabled,
        status=status,
        harvest=harvest,
        message_generator=message_generator,
    )

    # Task registry — Orchestrator sorts by priority automatically
    chat_session_max = config.get("chat_session_max_seconds", 600)

    # Optional tasks — each can be toggled in config["tasks"][name].
    # DialogTask and RecoveryTask are always active (bot infrastructure).
    optional = {
        "matched_profile": MatchedProfileTask(),                                         # priority  60
        "chat":            ChatTask(),                                                   # priority  50
        "sleep":           SleepTask(scheduler, sleep_interval, sleep_duration),        # priority  20
        "chat_queue":      ChatQueueTask(scheduler, likes_interval, chat_interval, chat_session_max),  # priority  15
        "switch_region":   SwitchRegionTask(scheduler, region_interval, region_nations),# priority   7
        "like_page":       LikePageTask(),                                               # priority  10
        "profile_eval":    ProfileEvalTask(),                                            # priority   5
        "swipe":           SwipeTask(),                                                  # priority   5
    }

    tasks = [
        DialogTask(),                                                                    # priority 100 (always)
        *[t for name, t in optional.items() if _on(name)],
        RecoveryTask(),                                                                  # priority   1 (always)
    ]
    enabled = [name for name in optional if _on(name)]
    print(f"[Bot] Active tasks: {enabled}")

    return Orchestrator(ctx, tasks), store


if __name__ == '__main__':
    if not emulator.is_running():
        emulator.start()
    else:
        print("[Emulator] Already running.")

    bot, store = build_bot()
    try:
        bot.run()
    finally:
        store.close()
