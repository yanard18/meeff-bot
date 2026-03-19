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

    # Scheduler + status bar (must exist before BotContext)
    scheduler = PeriodicScheduler()
    likes_interval  = config.get("likes_check_interval_minutes", 10) * 60
    chat_interval   = config.get("chat_queue_interval_minutes", 5) * 60
    sleep_interval  = config.get("sleep_interval_minutes", 30) * 60
    sleep_duration  = config.get("sleep_duration_minutes", 20) * 60

    # Prime timers so the first check fires after the configured interval,
    # not immediately on startup (scheduler._last defaults to epoch 0).
    scheduler.reset("likes")
    scheduler.reset("chat_queue")
    scheduler.reset("sleep")

    status = StatusBar(scheduler)
    status.register_timer("Likes check", "likes",      likes_interval)
    status.register_timer("Chat queue",  "chat_queue", chat_interval)
    status.register_timer("Sleep",       "sleep",      sleep_interval)

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

    tasks = [
        DialogTask(),                                                                    # priority 100
        MatchedProfileTask(),                                                            # priority  60
        ChatTask(),                                                                      # priority  50
        SleepTask(scheduler, sleep_interval, sleep_duration),                           # priority  20
        ChatQueueTask(scheduler, likes_interval, chat_interval, chat_session_max),      # priority  15
        LikePageTask(),                                                                  # priority  10
        ProfileEvalTask(),                                                               # priority   5
        SwipeTask(),                                                                     # priority   5
        RecoveryTask(),                                                                  # priority   1
    ]

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
