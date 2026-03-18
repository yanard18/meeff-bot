import os
import base64


class AIServiceError(Exception):
    """Raised when the AI service fails to return a usable result."""


class AIService:
    """The 'Brain' of the bot. Wraps Claude API for photo scoring and chat replies.

    Requires the ANTHROPIC_API_KEY environment variable to be set.

    Usage:
        ai = AIService(config["ai"])
        score = ai.score_profile_photo("/tmp/shot_123.png")
        reply = ai.generate_chat_reply(messages, persona)   # Phase 5
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

    def score_profile_photo(self, screenshot_path):
        """Rates the attractiveness of the person in a profile photo (0–100).

        Sends the image to Claude Vision. Returns 0 if no face is visible.

        Args:
            screenshot_path: Path to a PNG/JPEG of the profile photo.

        Returns:
            float: Score 0.0–100.0.

        Raises:
            AIServiceError: If the API call fails or the response is unparseable.
            FileNotFoundError: If screenshot_path does not exist.
        """
        if not os.path.exists(screenshot_path):
            raise FileNotFoundError(f"Screenshot not found: {screenshot_path}")

        with open(screenshot_path, 'rb') as f:
            image_data = base64.standard_b64encode(f.read()).decode('utf-8')

        client = self._get_client()
        message = client.messages.create(
            model=self.model,
            max_tokens=10,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_data
                        }
                    },
                    {
                        "type": "text",
                        "text": (
                            "Rate the physical attractiveness of the person in this photo "
                            "from 0 to 100. If no face is clearly visible, return 0. "
                            "Reply with only the number, nothing else."
                        )
                    }
                ]
            }]
        )

        raw = message.content[0].text.strip()
        try:
            score = float(raw)
            return max(0.0, min(100.0, score))
        except ValueError:
            raise AIServiceError(f"Could not parse score from model response: '{raw}'")

    def generate_chat_reply(self, conversation, persona):
        """Generates a natural chat reply given the conversation history.

        Args:
            conversation: list[dict] with keys "role" ("user"|"assistant")
                          and "content" (str). Last entry is always the
                          other person's latest message (role="user").
            persona: A string describing how the bot should present itself.
                     Loaded from config["ai"]["persona"].

        Returns:
            str: A short, natural reply ready to be typed into the chat.

        Raises:
            AIServiceError: If the API call fails or returns an empty response.

        Implementation note (Phase 5):
            1. Build system prompt from persona string.
            2. Pass conversation list directly to the messages API.
            3. Return message.content[0].text stripped of whitespace.
        """
        raise NotImplementedError("Phase 5: generate_chat_reply() not yet implemented.")
