import sys
import time

from .context import BotContext
from .task import Task


class Orchestrator:
    """App-agnostic main loop.

    Each tick:
      1. Ask the platform for the current UI state string.
      2. Update the status bar mode (renders independently in its own thread).
      3. Walk tasks in descending priority order.
      4. Call run() on the first eligible task.
      5. Sleep for loop_interval seconds.

    Nothing here knows about Meeff, Instagram, or any specific task —
    all that knowledge lives in Platform and Task subclasses.
    """

    def __init__(self, ctx: BotContext, tasks: list[Task]) -> None:
        self._ctx = ctx
        self._tasks = sorted(tasks, key=lambda t: t.priority, reverse=True)

    def verify_system(self) -> None:
        """Abort early if the device is not ready."""
        print("[*] Checking system and device...")
        adb = self._ctx.adb

        if not adb.is_device_connected():
            print("[!] No device connected. Exiting.")
            sys.exit(1)

        if not adb.is_device_awake():
            print("[!] Device is asleep. Please wake it up. Exiting.")
            sys.exit(1)

        while adb.is_screen_locked():
            print("[!] Device is LOCKED. Please unlock the screen to proceed...")
            time.sleep(5)

        print("[+] System checks passed.")

    def run(self) -> None:
        self.verify_system()

        status = self._ctx.status
        if status:
            status.start()

        loop_interval = self._ctx.config.get("loop_interval", 1.0)

        try:
            while True:
                state = self._ctx.platform.detect_state()
                print(f"[State] {state}")

                if status:
                    status.update_mode(state.removeprefix("ACTIVE (").removesuffix(")"))

                for task in self._tasks:
                    if task.is_eligible(state):
                        task.run(self._ctx, state)
                        break

                time.sleep(loop_interval)

        except KeyboardInterrupt:
            print("\n[*] Stopping Bot...")
        finally:
            if status:
                status.stop()
