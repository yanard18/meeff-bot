import time

from ..core.task import Task
from ..core.context import BotContext


class ChatTask(Task):
    """Manages an open individual chat conversation.

    UI state: "ACTIVE (Chat With Person)"
    Priority 50 — higher than swipe/likes so the bot stays in an active chat
    until it decides to leave, rather than being interrupted by the outer loop.

    Stay/leave is handled naturally by the tick system: as long as the chat UI
    is on screen, this task wins every tick. To leave, run() calls press_back()
    which changes the UI state and makes is_eligible() return False next tick.

    Per-tick flow (AI enabled):
      1. If waiting for a reply and timeout hasn't passed — do nothing this tick.
      2. If _should_leave() — press back and reset state.
      3. If a reply can be generated — send it and start waiting.

    Extension hooks:
      _get_messages()   — read messages from screen (Vision layer)
      _should_leave()   — conversation exit logic (silence, LLM, max turns, etc.)
      _generate_reply() — produce reply text via AI service
      _send_message()   — type + tap send via ADB
    """

    priority = 50

    _RESPONSE_TIMEOUT = 30  # seconds to wait for a reply before leaving

    def __init__(self) -> None:
        self._waiting_since: float | None = None

    def is_eligible(self, state: str) -> bool:
        return "Chat With Person" in state

    def run(self, ctx: BotContext, state: str) -> None:
        if not ctx.scoring_enabled:
            print("[Chat] AI disabled — exiting chat.")
            self._leave(ctx)
            return

        # If we sent a message last tick, check whether we're still waiting.
        if self._waiting_since is not None:
            elapsed = time.time() - self._waiting_since
            if elapsed < self._RESPONSE_TIMEOUT:
                print(f"[Chat] Waiting for reply ({elapsed:.0f}s / {self._RESPONSE_TIMEOUT}s)...")
                return  # do nothing — Orchestrator will tick us again
            print("[Chat] Response timeout — leaving chat.")
            self._leave(ctx)
            return

        messages = self._get_messages(ctx)

        if self._should_leave(ctx, messages):
            print("[Chat] Decided to leave chat.")
            self._leave(ctx)
            return

        reply = self._generate_reply(ctx, messages)
        if reply:
            self._send_message(ctx, reply)
            self._waiting_since = time.time()
            print("[Chat] Reply sent — waiting for response.")
        else:
            print("[Chat] No reply generated — leaving chat.")
            self._leave(ctx)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _leave(self, ctx: BotContext) -> None:
        ctx.adb.press_back()
        self._waiting_since = None
        time.sleep(2)

    # ------------------------------------------------------------------
    # Extension hooks — implement these for full AI chat
    # ------------------------------------------------------------------

    def _get_messages(self, ctx: BotContext) -> list[str]:
        """Return chat message history from the current screen."""
        return []

    def _should_leave(self, ctx: BotContext, messages: list[str]) -> bool:
        """Return True to exit the chat this tick.

        Hook: implement exit logic — silence timeout, LLM judgement,
        maximum message count, etc.
        """
        return True  # Phase 0: always leave immediately

    def _generate_reply(self, ctx: BotContext, messages: list[str]) -> str | None:
        """Generate a reply using the AI service.

        Hook: call ctx.ai.generate_chat_reply(messages) when implemented.
        """
        return None

    def _send_message(self, ctx: BotContext, text: str) -> None:
        """Type and send a message via ADB.

        Hook: call ctx.adb.type_text(text) + tap send when implemented.
        After sending, record via: ctx.harvest.record_message(profile_id, "sent", text)
        """
