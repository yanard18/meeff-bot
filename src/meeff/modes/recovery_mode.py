from ...engine.mode import Mode
from ...engine.context import BotContext


class RecoveryState(Mode):
    """Fallback state: relaunches the app when no other state matches.

    Set as the FSMEngine fallback — triggered automatically on any
    unrecognised UI string.
    """

    @property
    def name(self) -> str:
        return "RECOVERY"

    def execute(self, ctx: BotContext) -> None:
        print("[Recovery] Unrecognised UI — triggering safe escape...")
        ctx.adb.safe_escape()
