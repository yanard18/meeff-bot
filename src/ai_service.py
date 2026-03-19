import os


class AIServiceError(Exception):
    """Raised when the AI service fails to return a usable result."""


class AIService:
    """Wraps the Claude API. Currently used for future chat reply generation.

    Requires the ANTHROPIC_API_KEY environment variable to be set.
    """

    def __init__(self, ai_config):
        self.config = ai_config
        self.model = ai_config["model"]
        self._client = None  # Lazily initialized on first use

    def _get_client(self):
        """Returns a cached, authenticated Anthropic client."""
        if self._client is not None:
            return self._client

        import anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise AIServiceError("ANTHROPIC_API_KEY environment variable not set.")
        self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def chat_reply(self, system: str, messages: list[dict]) -> str:
        """Send a conversation to the model and return its reply.

        messages: list of {"role": "user"|"assistant", "content": str}
        """
        client = self._get_client()
        response = client.messages.create(
            model=self.model,
            max_tokens=150,
            system=system,
            messages=messages,
        )
        return response.content[0].text.strip()
