import time

from ..core.task import Task
from ..core.context import BotContext
from ..core.states import NOT_OPENED


class RecoveryTask(Task):
    """Fallback task: re-launches the app or escapes stuck states.

    Handles two scenarios:
      - "NOT OPENED": app is not running → launch it (up to 3 attempts).
      - Any other unrecognised state: increment a streak counter; after 3
        consecutive unknown ticks trigger safe_escape() to reset to a known
        state.

    Priority 1 — lowest, only runs when no other task matches.
    """

    priority = 1

    def __init__(self) -> None:
        self._launch_attempts = 0
        self._unknown_streak = 0

    def is_eligible(self, state: str) -> bool:
        return True

    def run(self, ctx: BotContext, state: str) -> None:
        if state == NOT_OPENED:
            self._unknown_streak = 0
            self._launch_attempts += 1
            if self._launch_attempts > 3:
                print(f"[Recovery] App failed to launch after {self._launch_attempts} attempts. Waiting 30s...")
                time.sleep(30)
                self._launch_attempts = 0
            else:
                print(f"[Recovery] App not open. Launching (attempt {self._launch_attempts}/3)...")
                ctx.adb.safe_escape()
        else:
            self._launch_attempts = 0
            self._unknown_streak += 1
            print(f"[Recovery] Unknown state (streak: {self._unknown_streak}/3): {state!r}")
            if self._unknown_streak >= 3:
                print("[Recovery] Stuck for 3 consecutive ticks — triggering safe escape.")
                ctx.adb.safe_escape()
                self._unknown_streak = 0
            else:
                time.sleep(3)
