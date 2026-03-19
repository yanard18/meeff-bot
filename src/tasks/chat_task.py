import time

from ..core.task import Task
from ..core.context import BotContext


class ChatTask(Task):
    """Manages an open individual chat conversation.

    UI state: "ACTIVE (Chat With Person)"
    Priority 50 — higher than swipe/likes so the bot stays in an active chat
    until it decides to leave, rather than being interrupted by the outer loop.

    Current behavior (Phase 0): exits the chat immediately.

    To enable AI replies (Phase 1+), implement _should_stay() and
    _generate_reply() below. The sub-loop structure is already in place:
    the bot will keep chatting until _should_stay() returns False.
    """

    priority = 50

    def is_eligible(self, state: str) -> bool:
        return "Chat With Person" in state

    def run(self, ctx: BotContext, state: str) -> None:
        if not ctx.scoring_enabled:
            # AI not configured — exit chat immediately (current behaviour).
            print("[Chat] AI disabled — exiting chat.")
            ctx.adb.press_back()
            time.sleep(2)
            return

        # ----------------------------------------------------------------
        # AI sub-loop: stays in this chat until _should_stay() says stop.
        # The outer Orchestrator loop is intentionally bypassed here so
        # the bot can hold a full conversation without losing context.
        # ----------------------------------------------------------------
        print("[Chat] Entering AI chat sub-loop...")
        while True:
            current = ctx.platform.detect_state()
            if "Chat With Person" not in current:
                print("[Chat] Left chat — returning to outer loop.")
                break

            messages = self._get_messages(ctx)
            if not self._should_stay(ctx, messages):
                print("[Chat] Decided to leave chat.")
                ctx.adb.press_back()
                time.sleep(2)
                break

            reply = self._generate_reply(ctx, messages)
            if reply:
                self._send_message(ctx, reply)

            # Wait for the other person to reply (or a timeout).
            self._wait_for_response(ctx, timeout=30)

    # ------------------------------------------------------------------
    # Extension hooks — override or implement these for AI chat
    # ------------------------------------------------------------------

    def _get_messages(self, ctx: BotContext) -> list[str]:
        """Return chat message history from the current screen.

        Hook: replace with ctx.vision.get_chat_messages() when implemented.
        """
        return []

    def _should_stay(self, ctx: BotContext, messages: list[str]) -> bool:
        """Decide whether to keep chatting or leave.

        Hook: implement conversation exit logic here (e.g. silence timeout,
        LLM judgement, maximum message count, etc.)
        """
        return False  # Phase 0: always leave immediately

    def _generate_reply(self, ctx: BotContext, messages: list[str]) -> str | None:
        """Generate a reply using the AI service.

        Hook: call ctx.ai.generate_chat_reply(messages) when implemented.
        """
        return None

    def _send_message(self, ctx: BotContext, text: str) -> None:
        """Type and send a message.

        Hook: call ctx.adb.type_text(text) + tap send when implemented.
        """

    def _wait_for_response(self, ctx: BotContext, timeout: int = 30) -> None:
        """Idle until a new message appears or timeout expires."""
        time.sleep(timeout)
