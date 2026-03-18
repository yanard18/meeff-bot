"""
Trainer for the CLIP-based image classifier.

Scans labeled image directories, embeds them with CLIP, fits a LogisticRegression,
and saves the model to a pickle file ready for ClipCritic.

Quick start:
    trainer = Trainer(liked_dir="labeled_data/liked", disliked_dir="labeled_data/disliked")
    trainer.train(output_path="classifier.pkl")
"""

import pickle
from pathlib import Path

import torch
import clip
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score


class Trainer:
    """Trains a CLIP-based binary image classifier.

    Args:
        liked_dir:    Directory of positively-labeled images.
        disliked_dir: Directory of negatively-labeled images.
        clip_model:   CLIP model variant. Default "ViT-B/32".
        device:       Torch device. Default "cpu".
        min_samples:  Minimum images per class required to train. Default 10.
    """

    IMAGE_EXTS = {"*.jpg", "*.jpeg", "*.png", "*.webp"}

    def __init__(
        self,
        liked_dir: str,
        disliked_dir: str,
        clip_model: str = "ViT-B/32",
        device: str = "cpu",
        min_samples: int = 10,
    ):
        self.liked_dir = Path(liked_dir)
        self.disliked_dir = Path(disliked_dir)
        self.clip_model = clip_model
        self.device = device
        self.min_samples = min_samples

    def _glob_images(self, directory: Path) -> list[Path]:
        paths = []
        for ext in self.IMAGE_EXTS:
            paths.extend(directory.glob(ext))
        return sorted(paths)

    def _embed_images(self, model, preprocess, paths: list[Path]) -> list:
        embeddings = []
        for p in paths:
            try:
                img = preprocess(Image.open(p).convert("RGB")).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    emb = model.encode_image(img).squeeze().cpu().numpy()
                embeddings.append(emb)
            except Exception as e:
                print(f"[Trainer] Skipping {p.name}: {e}")
        return embeddings

    def train(self, output_path: str = "classifier.pkl") -> None:
        """Embed all labeled images and fit a LogisticRegression classifier.

        Args:
            output_path: Where to save the classifier pickle.
        """
        liked_paths = self._glob_images(self.liked_dir)
        disliked_paths = self._glob_images(self.disliked_dir)

        print(f"[Trainer] Found {len(liked_paths)} liked, {len(disliked_paths)} disliked samples.")

        if len(liked_paths) < self.min_samples or len(disliked_paths) < self.min_samples:
            print(f"[Trainer] Need at least {self.min_samples} samples per class. Aborting.")
            return

        print(f"[Trainer] Loading CLIP ({self.clip_model})...")
        model, preprocess = clip.load(self.clip_model, device=self.device)

        print("[Trainer] Embedding images...")
        X = self._embed_images(model, preprocess, liked_paths) + \
            self._embed_images(model, preprocess, disliked_paths)
        y = [1] * len(liked_paths) + [0] * len(disliked_paths)

        print(f"[Trainer] Training on {len(y)} samples...")
        clf = LogisticRegression(max_iter=1000)
        clf.fit(X, y)

        if len(y) >= 20:
            cv_scores = cross_val_score(clf, X, y, cv=min(5, len(y) // 4))
            print(f"[Trainer] Cross-val accuracy: {cv_scores.mean():.0%} ± {cv_scores.std():.0%}")

        output = Path(output_path)
        with open(output, "wb") as f:
            pickle.dump(clf, f)

        print(f"[Trainer] Training accuracy: {clf.score(X, y):.0%}")
        print(f"[Trainer] Saved classifier → {output}")
