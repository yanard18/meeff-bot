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

    def score_profile_photo(self, screenshot_path, rules):
        """Scores the profile photo using the provided rules and returns (score, explanation).

        Args:
            screenshot_path: Path to a PNG/JPEG of the profile photo.
            rules: Plain-text scoring criteria from the critic configuration.

        Returns:
            tuple[float, str]: (score 0.0–100.0, one-sentence explanation)

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

        prompt = (
            f"{rules}\n\n"
            'Respond with a single JSON object, nothing else: '
            '{"score": <0-100>, "explanation": "<one sentence>"}'
        )

        client = self._get_client()
        message = client.messages.create(
            model=self.model,
            max_tokens=100,
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
        # Strip markdown code fences if the model wraps its JSON response
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:]).strip()
        try:
            data = _json.loads(raw)
            score = max(0.0, min(100.0, float(data["score"])))
            explanation = str(data.get("explanation", ""))
            return score, explanation
        except (KeyError, ValueError, _json.JSONDecodeError):
            raise AIServiceError(f"Could not parse critic response: '{raw}'")

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
