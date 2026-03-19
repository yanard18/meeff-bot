from ...engine.mode import Mode
from ...engine.context import BotContext
from ..profile_actions import evaluate_and_decide


class DetailedProfileState(Mode):
    """Evaluates an open profile and decides like or nope.

    UI: ACTIVE (Detailed Profile)
    """

    @property
    def name(self) -> str:
        return "Detailed Profile"

    def execute(self, ctx: BotContext) -> None:
        evaluate_and_decide(ctx)
