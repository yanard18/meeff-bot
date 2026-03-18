from dataclasses import dataclass


@dataclass
class CriticResult:
    score: float
    explanation: str
    liked: bool


class ProfileCritic:
    """Threshold-based evaluator: decides like or skip from a scored photo.

    Decoupled from any AI backend — accepts any scorer callable and a plain-text
    rules string, so the criteria and the LLM can both be swapped independently.

    Args:
        scorer:    callable(path: str, rules: str) -> tuple[float, str]
                   Returns (score 0–100, one-sentence explanation).
        threshold: Minimum score required to like. Default 60.
        rules:     Plain-text scoring criteria passed verbatim to the scorer.

    Example:
        critic = ProfileCritic(scorer=ai.score_profile_photo, threshold=65,
                               rules="Rate attractiveness 0-100. Penalise group photos.")
        result = critic.evaluate("/tmp/photo.jpg")
        print(result.score, result.explanation, result.liked)
    """

    def __init__(self, scorer, threshold=60, rules=""):
        self.scorer = scorer
        self.threshold = threshold
        self.rules = rules

    def evaluate(self, screenshot_path) -> CriticResult:
        """Score a photo and return a full CriticResult.

        Falls back to liked=True on missing screenshot or any scoring error,
        so a broken AI never blocks the bot.
        """
        if not screenshot_path:
            print("[Critic] No screenshot — defaulting to like.")
            return CriticResult(score=0.0, explanation="No screenshot available.", liked=True)
        try:
            score, explanation = self.scorer(screenshot_path, self.rules)
            liked = score >= self.threshold
            decision = "LIKE" if liked else "SKIP"
            print(f"[Critic] Score: {score:.0f}/100  threshold: {self.threshold}  → {decision}")
            print(f"[Critic] {explanation}")
            return CriticResult(score=score, explanation=explanation, liked=liked)
        except Exception as e:
            print(f"[Critic] Scoring failed: {e} — defaulting to skip.")
            return CriticResult(score=0.0, explanation=f"Scoring error: {e}", liked=False)
