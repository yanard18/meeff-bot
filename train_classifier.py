"""
CLIP-based preference classifier trainer.

Run this once you have collected enough labeled photos via the bot
(recommended: 50+ liked, 50+ disliked).

Usage:
    python train_classifier.py

Output:
    classifier.pkl  — drop-in model file used by ClipCritic
"""

import pickle
from pathlib import Path

import torch
import clip
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score


LIKED_DIR    = Path("labeled_data/liked")
DISLIKED_DIR = Path("labeled_data/disliked")
OUTPUT_PATH  = Path("classifier.pkl")


def load_and_embed(model, preprocess, paths):
    embeddings = []
    for p in paths:
        try:
            img = preprocess(Image.open(p).convert("RGB")).unsqueeze(0)
            with torch.no_grad():
                emb = model.encode_image(img).squeeze().cpu().numpy()
            embeddings.append(emb)
        except Exception as e:
            print(f"[!] Skipping {p.name}: {e}")
    return embeddings


def main():
    liked_paths    = sorted(LIKED_DIR.glob("*.png"))
    disliked_paths = sorted(DISLIKED_DIR.glob("*.png"))

    print(f"[*] Found {len(liked_paths)} liked, {len(disliked_paths)} disliked samples.")

    if len(liked_paths) < 10 or len(disliked_paths) < 10:
        print("[!] Not enough data. Collect at least 10 samples per class before training.")
        return

    print("[*] Loading CLIP model...")
    model, preprocess = clip.load("ViT-B/32", device="cpu")

    print("[*] Embedding images...")
    X = load_and_embed(model, preprocess, liked_paths) + \
        load_and_embed(model, preprocess, disliked_paths)
    y = [1] * len(liked_paths) + [0] * len(disliked_paths)

    print(f"[*] Training classifier on {len(y)} samples...")
    clf = LogisticRegression(max_iter=1000)
    clf.fit(X, y)

    if len(y) >= 20:
        cv_scores = cross_val_score(clf, X, y, cv=min(5, len(y) // 4))
        print(f"[*] Cross-val accuracy: {cv_scores.mean():.0%} ± {cv_scores.std():.0%}")

    with open(OUTPUT_PATH, "wb") as f:
        pickle.dump(clf, f)

    print(f"[+] Saved classifier to {OUTPUT_PATH}")
    print(f"[+] Training accuracy: {clf.score(X, y):.0%}")
    print("[+] Restart the bot to use the new model.")


if __name__ == "__main__":
    main()
