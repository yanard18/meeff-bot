import time

from ..core.task import Task
from ..core.context import BotContext


class ChatTask(Task):
    """Manages one open chat conversation.

    UI state: "ACTIVE (Chat With Person)"
    Priority 50.

    Stay/leave is handled naturally by the tick system: as long as the chat UI
    is on screen this task wins every tick. Pressing back changes the UI state
    so is_eligible() returns False, handing control back to ChatQueueTask.

    Per-tick flow:
      1. Resolve profile_id from the chat toolbar (once per session).
      2. If waiting for a reply and timeout has not passed — do nothing.
      3. If max turns reached — leave.
      4. Try to generate a reply via ctx.message_generator.
         If a reply is produced — send it, start waiting.
         If not — leave.

    Hot-chat detection: if new messages appear while we are waiting (the other
    person replied), _waiting_since is cleared so we re-enter the send loop
    instead of timing out.
    """

    priority = 50

    def __init__(self) -> None:
        self._reset_session_state()

    def _reset_session_state(self) -> None:
        self._waiting_since: float | None = None
        self._profile_id: str | None = None
        self._turns_sent: int = 0
        self._msg_count_at_send: int = 0
        self._recorded_msg_count: int = 0

    def is_eligible(self, state: str) -> bool:
        return "Chat With Person" in state

    def run(self, ctx: BotContext, state: str) -> None:
        if not ctx.scoring_enabled:
            print("[Chat] AI disabled — exiting chat.")
            self._leave(ctx)
            return

        # Resolve profile once per chat session
        if self._profile_id is None and ctx.harvest:
            self._profile_id = ctx.harvest.harvest_chat_contact()

        messages = self._get_messages(ctx)
        self._record_new_messages(ctx, messages)
        max_turns = ctx.config.get("chat_max_turns", 3)

        # Hot-chat detection: they replied while we were waiting
        if self._waiting_since is not None and len(messages) > self._msg_count_at_send:
            print("[Chat] They replied — resuming conversation.")
            self._waiting_since = None

        if self._waiting_since is not None:
            elapsed = time.time() - self._waiting_since
            timeout = ctx.config.get("chat_response_timeout", 30)
            if elapsed < timeout:
                print(f"[Chat] Waiting for reply ({elapsed:.0f}s / {timeout}s)...")
                return
            print("[Chat] Response timeout — leaving chat.")
            self._leave(ctx)
            return

        if self._turns_sent >= max_turns:
            print(f"[Chat] Reached {max_turns} turns — leaving chat.")
            self._leave(ctx)
            return

        profile = ctx.harvest.get_profile(self._profile_id) if (ctx.harvest and self._profile_id) else None
        reply = self._generate_reply(ctx, messages, profile)

        if reply:
            self._msg_count_at_send = len(messages)
            self._send_message(ctx, reply)
            self._turns_sent += 1
            self._waiting_since = time.time()
            print(f"[Chat] Message sent (turn {self._turns_sent}/{max_turns}) — waiting for reply.")
        else:
            print("[Chat] No reply generated — leaving chat.")
            self._leave(ctx)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _leave(self, ctx: BotContext) -> None:
        ctx.adb.press_back()
        self._reset_session_state()
        time.sleep(2)

    def _get_messages(self, ctx: BotContext) -> list[dict]:
        """Read visible messages from the current chat screen."""
        return ctx.vision.get_chat_messages()

    def _generate_reply(
        self,
        ctx: BotContext,
        messages: list[dict],
        profile: dict | None,
    ) -> str | None:
        """Delegate to the injected MessageGenerator."""
        if ctx.message_generator:
            return ctx.message_generator.generate(messages, profile)
        return None

    def _persist_message(self, ctx: BotContext, direction: str, text: str) -> None:
        if ctx.harvest and self._profile_id:
            ctx.harvest.record_message(self._profile_id, direction, text)
            self._recorded_msg_count += 1

    def _record_new_messages(self, ctx: BotContext, messages: list[dict]) -> None:
        """Persist any messages not yet saved to the profile DB."""
        if not ctx.harvest or not self._profile_id:
            return
        for msg in messages[self._recorded_msg_count:]:
            self._persist_message(ctx, msg["direction"], msg["text"])

    def _send_message(self, ctx: BotContext, text: str) -> None:
        # Step 1: tap the input field to give it focus
        input_field = ctx.vision.get_node_bounds("message_edittext")
        if not input_field:
            print("[Chat] message_edittext not found — cannot send.")
            return
        ctx.adb.human_tap(input_field, name="Message Input")
        time.sleep(1.0)  # wait for soft keyboard to appear

        # Step 2: type character by character with human-like timing
        ctx.adb.type_text_human(text)

        # Step 3: refresh UI — keyboard shifts layout, old coords are stale
        ctx.vision.refresh_screen_data()
        time.sleep(0.3)

        # Step 4: tap send with fresh coordinates
        send = ctx.vision.get_node_bounds("send_imageview")
        if send:
            ctx.adb.human_tap(send, name="Send")
        else:
            print("[Chat] send_imageview not found after typing.")

        # Step 5: dismiss keyboard so next tick reads clean layout
        time.sleep(0.5)
        ctx.adb.press_back()
        time.sleep(0.5)

        self._persist_message(ctx, "sent", text)
