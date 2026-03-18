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

    def classify_profile_photo(self, screenshot_path, questions):
        """Asks factual yes/no questions about a profile photo and returns the answers.

        The LLM is never asked to rate or judge — only to observe facts.
        Scoring is computed by the caller (ProfileCritic) from the returned dict.

        Args:
            screenshot_path: Path to a PNG/JPEG of the profile photo.
            questions: list of dicts with keys "key" (str) and "text" (str question).

        Returns:
            dict[str, bool]: Maps each question key to True or False.

        Raises:
            AIServiceError: If the API call fails or the response is unparseable.
            FileNotFoundError: If screenshot_path does not exist.
        """
        import json as _json

        if not os.path.exists(screenshot_path):
            raise FileNotFoundError(f"Screenshot not found: {screenshot_path}")

        ext = os.path.splitext(screenshot_path)[1].lower()
        media_type = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"

        with open(screenshot_path, 'rb') as f:
            image_data = base64.standard_b64encode(f.read()).decode('utf-8')

        keys = [q["key"] for q in questions]
        question_lines = "\n".join(f'- {q["key"]}: {q["text"]}' for q in questions)
        example = "{" + ", ".join(f'"{k}": true' for k in keys) + "}"
        prompt = (
            "Answer each question about this photo with true or false.\n"
            "Respond with ONLY a JSON object — no explanation, no extra text.\n\n"
            f"Questions:\n{question_lines}\n\n"
            f"Required format: {example}"
        )

        client = self._get_client()
        message = client.messages.create(
            model=self.model,
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data
                        }
                    },
                    {"type": "text", "text": prompt}
                ]
            }]
        )

        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:]).strip()
        try:
            data = _json.loads(raw)
            return {k: bool(data[k]) for k in keys}
        except (KeyError, ValueError, _json.JSONDecodeError):
            raise AIServiceError(f"Could not parse classifier response: '{raw}'")

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
