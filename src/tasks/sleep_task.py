import time

from ..core.task import Task
from ..core.context import BotContext
from ..core.scheduler import PeriodicScheduler


class SleepTask(Task):
    """Periodically closes the app and idles to mimic a real user taking breaks.

    Fires every `sleep_interval` seconds. When triggered:
      1. Close Meeff and clear RAM (kill_app).
      2. Sleep for `sleep_duration` seconds.
      3. Relaunch Meeff.

    Priority 20 — below DialogTask (100), MatchedProfileTask (60), and
    ChatTask (50) so active conversations and dialogs finish first, but
    above ChatQueueTask (15) and everything else so routine work is
    interrupted cleanly.
    """

    priority = 20

    def __init__(
        self,
        scheduler: PeriodicScheduler,
        sleep_interval: float,
        sleep_duration: float,
    ) -> None:
        self._scheduler = scheduler
        self._sleep_interval = sleep_interval
        self._sleep_duration = sleep_duration

    def is_eligible(self, state: str) -> bool:
        return self._scheduler.is_due("sleep", self._sleep_interval)

    def run(self, ctx: BotContext, state: str) -> None:
        self._scheduler.reset("sleep")
        duration_min = self._sleep_duration / 60
        print(f"[Sleep] Break time — closing app and sleeping for {duration_min:.0f} minutes.")
        ctx.adb.kill_app()
        time.sleep(self._sleep_duration)
        print("[Sleep] Waking up — relaunching Meeff.")
        ctx.adb.launch_app()
