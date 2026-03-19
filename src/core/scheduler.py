import time


class PeriodicScheduler:
    """Tracks named timers for rate-limited periodic actions.

    Usage:
        scheduler = PeriodicScheduler()

        if scheduler.is_due("likes", interval_secs=600):
            scheduler.reset("likes")
            do_likes_check()
    """

    def __init__(self) -> None:
        self._last: dict[str, float] = {}

    def is_due(self, name: str, interval_secs: float) -> bool:
        """Return True if at least `interval_secs` have passed since the last reset."""
        return time.time() - self._last.get(name, 0.0) >= interval_secs

    def reset(self, name: str) -> None:
        """Mark `name` as just-executed (restarts its interval)."""
        self._last[name] = time.time()

    def time_remaining(self, name: str, interval_secs: float) -> float:
        """Seconds until `name` is next due. Returns 0.0 if already overdue."""
        elapsed = time.time() - self._last.get(name, 0.0)
        return max(0.0, interval_secs - elapsed)
