"""MessageGenerator — protocol and implementations.

Any object that implements generate() can be injected into BotContext and used
by ChatTask. Swap implementations without touching any task code.

Implementations:
  AIMessageGenerator  — sends openers from config, then uses Claude for replies
"""

import random
from typing import Protocol, runtime_checkable

from ..ai_service import AIService, AIServiceError


@runtime_checkable
class MessageGenerator(Protocol):
    def generate(
        self,
        messages: list[dict],
        profile: dict | None,
    ) -> str | None:
        """Return a reply string, or None to skip and leave the chat.

        Args:
            messages: DB chat history [{text, direction}, ...], oldest first.
            profile:  harvested profile dict from ProfileStore, or None.
        """


class AIMessageGenerator:
    """Generates chat replies using Claude.

    For empty conversations, returns a random opener from config (no API call).
    For ongoing conversations, builds a message history and calls the model.

    Config keys (from chat_persona block in config.json):
      system_prompt — persona/style instructions for the model
      openers       — list of first-contact opener strings
    """

    def __init__(self, ai: AIService, persona_config: dict) -> None:
        self._ai = ai
        self._system = persona_config.get("system_prompt", "")
        self._openers = persona_config.get("openers", [])

    def generate(self, messages: list[dict], profile: dict | None) -> str | None:
        we_spoke = any(m["direction"] == "sent" for m in messages)
        if not we_spoke:
            if not self._openers:
                return None
            return random.choice(self._openers)

        anthropic_msgs = [
            {
                "role": "assistant" if m["direction"] == "sent" else "user",
                "content": m["text"],
            }
            for m in messages
        ]

        try:
            return self._ai.chat_reply(self._system, anthropic_msgs)
        except AIServiceError as e:
            print(f"[AIMessageGenerator] API error: {e}")
            return None
