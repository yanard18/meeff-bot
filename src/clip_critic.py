"""
CLIP-based profile critic.

Drop-in replacement for ProfileCritic once classifier.pkl has been trained.
No LLM calls, no API costs, no ethics refusals — runs entirely locally.

Usage in bot_controller.py:
    from .clip_critic import ClipCritic
    self.critic = ClipCritic(threshold=0.6)
"""

import os
import pickle
from dataclasses import dataclass

import torch
import clip
from PIL import Image


@dataclass
class CriticResult:
    score: float
    answers: dict
    liked: bool


class ClipCritic:
    """Scores a profile photo using a locally trained CLIP-based classifier.

    Requires classifier.pkl to exist (produced by train_classifier.py).

    Args:
        classifier_path: Path to the trained sklearn classifier pickle.
        threshold:       Minimum probability (0.0–1.0) to like. Default 0.6.
    """

    CLASSIFIER_PATH = "classifier.pkl"

    def __init__(self, threshold=0.6):
        self.threshold = threshold
        self._model = None
        self._preprocess = None
        self._clf = None

    def _load(self):
        """Lazy-loads CLIP and the trained classifier on first use."""
        if self._clf is not None:
            return

        if not os.path.exists(self.CLASSIFIER_PATH):
            raise FileNotFoundError(
                f"No classifier found at '{self.CLASSIFIER_PATH}'. "
                "Run train_classifier.py first."
            )

        print("[ClipCritic] Loading CLIP model (first run may take a moment)...")
        self._model, self._preprocess = clip.load("ViT-B/32", device="cpu")

        with open(self.CLASSIFIER_PATH, "rb") as f:
            self._clf = pickle.load(f)

        print("[ClipCritic] Ready.")

    def evaluate(self, screenshot_path) -> CriticResult:
        """Embed the photo and return a scored CriticResult.

        Fails closed (liked=False) on any error so a broken model
        never incorrectly approves a profile.
        """
        if not screenshot_path or not os.path.exists(screenshot_path):
            print("[ClipCritic] No screenshot — skipping.")
            return CriticResult(score=0.0, answers={}, liked=False)

        try:
            self._load()

            img = self._preprocess(
                Image.open(screenshot_path).convert("RGB")
            ).unsqueeze(0)

            with torch.no_grad():
                embedding = self._model.encode_image(img).squeeze().cpu().numpy()

            prob = self._clf.predict_proba([embedding])[0][1]
            score = round(prob * 100, 1)
            liked = prob >= self.threshold
            decision = "LIKE" if liked else "SKIP"
            print(f"[ClipCritic] Score: {score}/100  threshold: {self.threshold * 100:.0f}  → {decision}")

            return CriticResult(score=score, answers={}, liked=liked)

        except Exception as e:
            print(f"[ClipCritic] Failed: {e} — defaulting to skip.")
            return CriticResult(score=0.0, answers={}, liked=False)
