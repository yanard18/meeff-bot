from dataclasses import dataclass


@dataclass
class CriticResult:
    score: float
    answers: dict
    liked: bool


class ProfileCritic:
    """Evaluates a profile photo via binary QA and scores it entirely in Python.

    The LLM is only asked factual yes/no questions (no judgment, no rating).
    Scoring logic lives here, driven by weights and disqualifiers from config.

    Args:
        classifier:    callable(path, questions) -> dict[str, bool]
        questions:     list of {"key": str, "text": str} dicts passed to the classifier.
        disqualifiers: list of question keys that must be True to pass.
                       If any disqualifier is False, score is 0 and liked is False.
        weights:       dict[str, int] — points added when a key is True (use negative for penalties).
        threshold:     Minimum score to like. Default 60.
    """

    def __init__(self, classifier, questions, disqualifiers, weights, threshold=60):
        self.classifier = classifier
        self.questions = questions
        self.disqualifiers = disqualifiers
        self.weights = weights
        self.threshold = threshold
        self._validate_config()

    def _validate_config(self):
        """Warns at startup if any weight key or disqualifier has no matching question."""
        question_keys = {q["key"] for q in self.questions}
        all_keys = set(self.weights.keys()) | set(self.disqualifiers)
        orphaned = all_keys - question_keys
        if orphaned:
            print(f"[Critic] WARNING: these keys have no question defined and will always be False: {sorted(orphaned)}")
            print(f"[Critic] Add a matching entry in config 'questions' for each key above.")

    def _compute_score(self, answers: dict) -> float:
        """Applies disqualifiers then sums weights. All logic is here, not in the LLM."""
        for key in self.disqualifiers:
            if not answers.get(key, False):
                print(f"[Critic] Disqualifier failed: {key}=False → score 0")
                return 0.0

        score = sum(
            weight for key, weight in self.weights.items()
            if answers.get(key, False)
        )
        return max(0.0, min(100.0, float(score)))

    def evaluate(self, screenshot_path) -> CriticResult:
        """Classify the photo, compute score, return CriticResult.

        Fails closed (liked=False) on missing screenshot or any error,
        so a broken AI never incorrectly approves a profile.
        """
        if not screenshot_path:
            print("[Critic] No screenshot — skipping.")
            return CriticResult(score=0.0, answers={}, liked=False)
        try:
            answers = self.classifier(screenshot_path, self.questions)
            score = self._compute_score(answers)
            liked = score >= self.threshold
            decision = "LIKE" if liked else "SKIP"
            print(f"[Critic] Answers: {answers}")
            print(f"[Critic] Score: {score:.0f}/100  threshold: {self.threshold}  → {decision}")
            return CriticResult(score=score, answers=answers, liked=liked)
        except Exception as e:
            print(f"[Critic] Classification failed: {e} — defaulting to skip.")
            return CriticResult(score=0.0, answers={}, liked=False)
