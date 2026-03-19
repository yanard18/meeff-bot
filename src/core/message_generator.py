"""MessageGenerator — protocol and default implementations.

Any object that implements generate() can be injected into BotContext and used
by ChatTask. Swap implementations without touching any task code.

Implementations:
  TemplateGenerator — cycles through a static list of openers (Phase 1)
  Future: LLMGenerator — calls Claude/GPT with chat history context from ProfileStore
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class MessageGenerator(Protocol):
    def generate(
        self,
        messages: list[dict],
        profile: dict | None,
    ) -> str | None:
        """Return a reply string, or None to skip and leave the chat.

        Args:
            messages: visible messages [{text, direction}, ...], oldest first.
            profile:  harvested profile dict from ProfileStore, or None.
        """


class TemplateGenerator:
    """Sends one opener per new conversation, then stays silent (Phase 1).

    Cycles through a configured list of opener strings. Only sends when no
    messages are visible yet (first contact). Returns None for all subsequent
    turns so ChatTask leaves after the opener is delivered.

    Replacing this with an LLM-backed generator requires only swapping the
    MessageGenerator injected into BotContext — no task code changes.
    """

    def __init__(self, openers: list[str]) -> None:
        self._openers = openers
        self._index = 0

    def generate(self, messages: list[dict], profile: dict | None) -> str | None:
        if not self._openers:
            return None
        # Only send an opener when the conversation is empty (first contact)
        if messages:
            return None
        opener = self._openers[self._index % len(self._openers)]
        self._index += 1
        return opener
