from .context import BotContext
from .mode import Mode


class FSMEngine:
    """App-agnostic UI-driven FSM loop.

    Each tick:
      1. Detect current UI string.
      2. Find the first registered Mode whose matches() returns True.
      3. If the matched Mode differs from the active one, transition to it.
      4. Execute the active Mode.

    Nothing in this class knows about Meeff or any specific app.
    """

    def __init__(self, ctx: BotContext):
        self._ctx = ctx
        self._states: list[Mode] = []   # checked in order; first match wins
        self._fallback: Mode | None = None
        self._active: Mode | None = None

    def register_state(self, state: Mode) -> None:
        self._states.append(state)

    def set_fallback(self, state: Mode) -> None:
        """State used when no registered state matches the current UI."""
        self._fallback = state

    def _find_state(self, ui_string: str) -> Mode | None:
        for state in self._states:
            if state.matches(ui_string):
                return state
        return self._fallback

    def _transition_to(self, state: Mode) -> None:
        self._ctx.launch_attempts = 0
        state.on_enter(self._ctx)
        self._active = state
        print(f"[FSM] ── {state.name}")

    def run(self) -> None:
        print("\n" + "=" * 40)
        print("    FSM Bot Started")
        print("    Press Ctrl+C to stop")
        print("=" * 40 + "\n")

        try:
            while True:
                ui_string = self._ctx.vision.determine_app_state()
                state = self._find_state(ui_string)
                print(f"[UI] {ui_string}  [State] {state.name if state else '?'}")

                if state is not self._active:
                    self._transition_to(state)

                self._active.execute(self._ctx)

        except KeyboardInterrupt:
            print("\n[*] Stopping Bot...")
