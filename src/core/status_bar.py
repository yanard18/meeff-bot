import sys
import time
import threading
import shutil

from .scheduler import PeriodicScheduler

_RED    = "\033[91;1m"   # bright red + bold  (< 30 s)
_YELLOW = "\033[93m"     # yellow              (< 120 s)
_RESET  = "\033[0m"

_URGENT_SECS  = 30
_WARNING_SECS = 120
_BAR_WIDTH    = 20


class StatusBar:
    """Fixed status bar pinned to the top of the terminal.

    Uses an ANSI scroll region so log output scrolls below without ever
    pushing the bar off screen. A daemon thread redraws every second.
    sys.stdout is wrapped with an RLock so print() and the render thread
    are always serialised — no interleaved output.

    Layout (2 timers → HEIGHT = 6):
        ═══════════════════════════════════════════════════════
         MODE  Swipe Mode                 P:5  L:3  N:2  12:34
         ───────────────────────────────────────────────────────
         Matched check   [████░░░░░░░░░░░░░░░░]  01:45    ← yellow
         Likes check     [████████████░░░░░░░░]  05:12
        ═══════════════════════════════════════════════════════

    Timers are sorted shortest-remaining first so the most urgent task
    is always at the top of the list. The bar fill shows time *remaining*
    (full = just reset, empty = due now).
    """

    def __init__(self, scheduler: PeriodicScheduler) -> None:
        self._scheduler = scheduler
        self._lock = threading.RLock()
        self._mode = "Starting..."
        self._timers: list[tuple[str, str, float]] = []  # (label, key, interval_secs)
        self._stats: dict[str, int] = {}
        self._height = 0
        self._running = False
        self._thread: threading.Thread | None = None
        self._raw = sys.stdout   # saved before wrapping

    # ------------------------------------------------------------------
    # Configuration — call before start()
    # ------------------------------------------------------------------

    def register_timer(self, label: str, key: str, interval_secs: float) -> None:
        """Register a scheduler timer to display as a row in the bar."""
        self._timers.append((label, key, interval_secs))

    # ------------------------------------------------------------------
    # Runtime updates — called by Orchestrator and tasks
    # ------------------------------------------------------------------

    def update_mode(self, mode: str) -> None:
        with self._lock:
            self._mode = mode

    def increment(self, name: str, by: int = 1) -> None:
        """Increment a named counter shown in the header (profiles/likes/nopes)."""
        with self._lock:
            self._stats[name] = self._stats.get(name, 0) + by

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        # top sep + mode line + inner sep + N timer rows + bottom sep
        self._height = len(self._timers) + 4

        self._raw.write("\033[2J\033[H")                    # clear screen
        self._raw.write(f"\033[{self._height + 1};9999r")   # scroll region below bar
        self._raw.write(f"\033[{self._height + 1};1H")      # park cursor in log area
        self._raw.flush()

        sys.stdout = _LockedStream(self._raw, self._lock)

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        sys.stdout = self._raw
        self._raw.write("\033[r\033[2J\033[H")
        self._raw.flush()

    # ------------------------------------------------------------------
    # Render loop
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        while self._running:
            self._render()
            time.sleep(1)

    def _render(self) -> None:
        cols = shutil.get_terminal_size().columns

        with self._lock:
            mode  = self._mode
            stats = dict(self._stats)

            # Sort timers: shortest remaining → top (most urgent first)
            rows = sorted(
                (
                    (self._scheduler.time_remaining(key, interval), label, interval)
                    for label, key, interval in self._timers
                ),
                key=lambda e: e[0],
            )

            sep  = "═" * cols
            thin = "─" * cols
            lines = [sep]

            # Header: mode + counters + clock
            p, lk, n = (stats.get(k, 0) for k in ("profiles", "likes", "nopes"))
            right = f"P:{p}  L:{lk}  N:{n}   {time.strftime('%H:%M:%S')} "
            left  = f" MODE  {mode}"
            pad   = " " * max(1, cols - len(left) - len(right))
            lines.append((left + pad + right)[:cols])
            lines.append(thin)

            # One row per timer
            for remaining, label, interval in rows:
                tm, ts  = divmod(int(remaining), 60)
                filled  = max(0, min(_BAR_WIDTH, int(remaining / interval * _BAR_WIDTH)))
                bar     = "█" * filled + "░" * (_BAR_WIDTH - filled)
                row     = f"  {label:<16} [{bar}]  {tm:02d}:{ts:02d}"

                if remaining < _URGENT_SECS:
                    row = f"{_RED}{row}{_RESET}"
                elif remaining < _WARNING_SECS:
                    row = f"{_YELLOW}{row}{_RESET}"

                lines.append(row)

            lines.append(sep)

            # Save cursor → absolute top → print → restore
            out = "\033[s\033[H"
            for line in lines[: self._height]:
                out += f"\033[2K{line}\r\n"
            out += "\033[u"

            self._raw.write(out)
            self._raw.flush()


class _LockedStream:
    """Wraps sys.stdout so every print() acquires the render lock first."""

    def __init__(self, stream, lock: threading.RLock) -> None:
        self._stream = stream
        self._lock   = lock

    def write(self, s: str) -> int:
        with self._lock:
            return self._stream.write(s)

    def flush(self) -> None:
        self._stream.flush()

    def __getattr__(self, name: str):
        return getattr(self._stream, name)
