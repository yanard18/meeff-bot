import random
import time

from ..core.task import Task
from ..core.context import BotContext
from ..core.scheduler import PeriodicScheduler
from ..core.states import SWIPE_MODE, SEARCH_FILTERS, NATIONALITY_PICKER


class SwitchRegionTask(Task):
    """Periodically rotates the nationality filter to broaden the profile pool.

    Every `interval` seconds (when on SWIPE_MODE):
      1. Tap the filter button → Search Filters screen.
      2. Tap "Add Nationality" → Nationality Picker popup.
      3. Search for a randomly chosen nationality, select it, Apply.
      4. Tap Apply on Search Filters → returns to Swipe.

    Nationality list comes from config["region_rotation"]["nationalities"].
    Selection is case-insensitive against the app's checkbox text.

    Priority 7 — beats SwipeTask (5) so the timer fires promptly, but yields
    to everything else (chat, dialogs, etc.).
    """

    priority = 7

    def __init__(
        self,
        scheduler: PeriodicScheduler,
        interval: float,
        nationalities: list[str],
    ) -> None:
        self._scheduler = scheduler
        self._interval = interval
        self._nationalities = nationalities
        self._active = False
        self._picker_opened = False
        self._target: str | None = None

    def is_eligible(self, state: str) -> bool:
        if self._active:
            if state in (SEARCH_FILTERS, NATIONALITY_PICKER):
                return True
            # Landed on unexpected state while mid-sequence — clean up silently
            self._reset()
            return False
        return state == SWIPE_MODE and self._scheduler.is_due("switch_region", self._interval)

    def run(self, ctx: BotContext, state: str) -> None:
        if state == SWIPE_MODE:
            self._start(ctx)

        elif state == SEARCH_FILTERS:
            if not self._picker_opened:
                self._open_picker(ctx)
            else:
                self._apply_filters(ctx)

        elif state == NATIONALITY_PICKER:
            self._select_nationality(ctx)

    # ------------------------------------------------------------------
    # Phase handlers
    # ------------------------------------------------------------------

    def _start(self, ctx: BotContext) -> None:
        if not self._nationalities:
            print("[SwitchRegion] No nationalities configured — skipping.")
            self._scheduler.reset("switch_region")
            return

        self._target = random.choice(self._nationalities)
        self._scheduler.reset("switch_region")
        self._active = True
        self._picker_opened = False
        print(f"[SwitchRegion] Switching region to: {self._target}")

        filter_btn = ctx.vision.get_node_bounds("filter_imageview")
        if not filter_btn:
            print("[SwitchRegion] filter_imageview not found — aborting.")
            self._reset()
            return
        ctx.adb.human_tap(filter_btn, name="Filter")
        time.sleep(1.5)

    def _open_picker(self, ctx: BotContext) -> None:
        picker_btn = ctx.vision.get_node_bounds("nationality_plus_layout")
        if not picker_btn:
            print("[SwitchRegion] nationality_plus_layout not found — aborting.")
            self._abort(ctx)
            return
        ctx.adb.human_tap(picker_btn, name="Add Nationality")
        self._picker_opened = True
        time.sleep(1.5)

    def _select_nationality(self, ctx: BotContext) -> None:
        search = ctx.vision.get_node_bounds("search_edittext")
        if not search:
            print("[SwitchRegion] search_edittext not found — aborting.")
            self._abort(ctx)
            return

        ctx.adb.human_tap(search, name="Search Nationality")
        time.sleep(0.5)
        ctx.adb.type_text_human(self._target)
        time.sleep(0.8)

        ctx.vision.refresh_screen_data()

        checkbox = ctx.vision.get_node_bounds_by_text("nationality_checkbox", self._target)
        if not checkbox:
            print(f"[SwitchRegion] '{self._target}' not found in picker — aborting.")
            self._abort(ctx)
            return

        ctx.adb.human_tap(checkbox, name=f"Select {self._target}")
        time.sleep(0.5)

        apply_btn = ctx.vision.get_node_bounds("next_textview")
        if not apply_btn:
            print("[SwitchRegion] Apply button not found in picker — aborting.")
            self._abort(ctx)
            return
        ctx.adb.human_tap(apply_btn, name="Apply Nationality")
        time.sleep(1.0)

    def _apply_filters(self, ctx: BotContext) -> None:
        apply_btn = ctx.vision.get_node_bounds("next_textview")
        if apply_btn:
            ctx.adb.human_tap(apply_btn, name="Apply Filters")
            time.sleep(1.0)
        else:
            print("[SwitchRegion] Apply button not found on filters screen — aborting.")
            self._abort(ctx)
            return
        print(f"[SwitchRegion] Region switched to: {self._target}")
        self._reset()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _reset(self) -> None:
        self._active = False
        self._picker_opened = False
        self._target = None

    def _abort(self, ctx: BotContext) -> None:
        print("[SwitchRegion] Aborting — pressing back.")
        ctx.adb.press_back()
        time.sleep(1.0)
        self._reset()
