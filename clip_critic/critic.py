"""
CLIP-based image classifier.

Scores images using a locally-trained CLIP + LogisticRegression pipeline.
No API calls, no external costs — runs entirely on-device.

Quick start:
    critic = ClipCritic(model_path="classifier.pkl", threshold=0.6)
    result = critic.evaluate("photo.jpg")
    print(result.score, result.liked)
"""

import os
import pickle
from dataclasses import dataclass

import torch
import clip
from PIL import Image

# ANSI color helpers
_R = "\033[0m"
_BOLD = "\033[1m"

def _score_color(score: float) -> str:
    """Red → yellow → green gradient based on 0–100 score."""
    if score >= 70:
        return "\033[92m"   # bright green
    elif score >= 50:
        return "\033[93m"   # bright yellow
    else:
        return "\033[91m"   # bright red


def _score_bar(score: float, width: int = 20) -> str:
    """Colored ASCII progress bar representing the score."""
    filled = int(round(score / 100 * width))
    col = _score_color(score)
    bar = col + "█" * filled + "\033[90m" + "░" * (width - filled) + _R
    return f"[{bar}]"


@dataclass
class CriticResult:
    score: float  # 0–100
    liked: bool


class ClipCritic:
    """Scores an image using a locally-trained CLIP-based classifier.

    Args:
        model_path:  Path to the trained sklearn classifier pickle.
        threshold:   Minimum probability (0.0–1.0) to return liked=True. Default 0.6.
        clip_model:  CLIP model variant. Default "ViT-B/32".
        device:      Torch device. Default "cpu".
    """

    def __init__(
        self,
        model_path: str = "classifier.pkl",
        threshold: float = 0.6,
        clip_model: str = "ViT-B/32",
        device: str = "cpu",
    ):
        self.model_path = model_path
        self.threshold = threshold
        self.clip_model = clip_model
        self.device = device
        self._model = None
        self._preprocess = None
        self._clf = None

    def _load(self):
        """Lazy-loads CLIP and the trained classifier on first use."""
        if self._clf is not None:
            return

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"No classifier found at '{self.model_path}'. "
                "Run Trainer.train() or train_classifier.py first."
            )

        print(f"[ClipCritic] Loading CLIP ({self.clip_model})...")
        self._model, self._preprocess = clip.load(self.clip_model, device=self.device)

        with open(self.model_path, "rb") as f:
            self._clf = pickle.load(f)

        print("[ClipCritic] Ready.")

    def embed(self, image_path: str):
        """Return the raw CLIP embedding for an image (512-D numpy array)."""
        self._load()
        img = self._preprocess(
            Image.open(image_path).convert("RGB")
        ).unsqueeze(0).to(self.device)
        with torch.no_grad():
            return self._model.encode_image(img).squeeze().cpu().numpy()

    def evaluate(self, image_path: str) -> CriticResult:
        """Score an image and return a CriticResult.

        Fails closed (liked=False) on any error so a broken model
        never incorrectly approves an image.
        """
        if not image_path or not os.path.exists(image_path):
            print("[ClipCritic] No image found — skipping.")
            return CriticResult(score=0.0, liked=False)

        try:
            self._load()
            embedding = self.embed(image_path)
            prob = self._clf.predict_proba([embedding])[0][1]
            score = round(prob * 100, 1)
            liked = prob >= self.threshold
            col = _score_color(score)
            bar = _score_bar(score)
            decision_fmt = f"\033[92m{_BOLD}✔ LIKE{_R}" if liked else f"\033[91m{_BOLD}✘ SKIP{_R}"
            threshold_pct = f"{self.threshold * 100:.0f}"
            print(
                f"\n[ClipCritic] {bar}  {col}{_BOLD}{score:5.1f}/100{_R}"
                f"  (threshold: {threshold_pct})  →  {decision_fmt}\n"
            )
            return CriticResult(score=score, liked=liked)

        except Exception as e:
            print(f"[ClipCritic] Failed: {e} — defaulting to skip.")
            return CriticResult(score=0.0, liked=False)
