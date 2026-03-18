"""
Train the CLIP image classifier.

Usage:
    python train_classifier.py

Output:
    classifier.pkl  — model file used by ClipCritic
"""

from clip_critic import Trainer

if __name__ == "__main__":
    trainer = Trainer(
        liked_dir="labeled_data/liked",
        disliked_dir="labeled_data/disliked",
    )
    trainer.train(output_path="classifier.pkl")
