import os


class AIServiceError(Exception):
    """Raised when the AI service fails to return a usable result."""


class AIService:
    """The 'Brain' of the bot. Wraps Claude API for photo scoring and chat replies.

    Requires the ANTHROPIC_API_KEY environment variable to be set.

    Usage:
        ai = AIService(config["ai"])
        score = ai.score_profile_photo("/tmp/shot_123.png")   # Phase 2
        reply = ai.generate_chat_reply(messages, persona)     # Phase 5
    """

    def __init__(self, ai_config):
        """
        Args:
            ai_config: The "ai" block from config.json.
        """
        self.config = ai_config
        self.model = ai_config["model"]
        self._client = None  # Lazily initialized in Phase 2

    def _get_client(self):
        """Returns an authenticated Anthropic client.

        Implementation note (Phase 2):
            import anthropic
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise AIServiceError("ANTHROPIC_API_KEY environment variable not set.")
            self._client = anthropic.Anthropic(api_key=api_key)
        """
        raise NotImplementedError("Phase 2: Anthropic client initialization not yet implemented.")

    def score_profile_photo(self, screenshot_path):
        """Scores a profile photo using Claude's vision capability.

        Sends the image to the model with a structured prompt asking for a
        numerical attractiveness/quality score. Returns a float 0.0–10.0.

        Args:
            screenshot_path: Absolute path to a PNG/JPEG of the profile photo.

        Returns:
            float: Score from 0.0 (skip) to 10.0 (definitely like).

        Raises:
            AIServiceError: If the API call fails or returns an unparseable response.
            FileNotFoundError: If screenshot_path does not exist.

        Implementation note (Phase 2):
            1. Read image bytes and base64-encode.
            2. Build a message with image + text prompt asking for a score.
            3. Parse the integer/float from the model's response.
            4. Return float(score).
        """
        raise NotImplementedError("Phase 2: score_profile_photo() not yet implemented.")

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
