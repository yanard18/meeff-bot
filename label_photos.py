"""
Manual photo labeling tool for CLIP training data.

Three modes:
  python label_photos.py              — label new/unlabeled photos from a folder
  python label_photos.py --review     — re-review already labeled photos to fix mistakes
  python label_photos.py --stats      — show dataset statistics only

Controls:
  y / Enter  → liked
  n          → disliked
  s          → skip (leave in place, decide later)
  q          → quit and save progress
"""

import argparse
import os
import shutil
import subprocess
import sys
import termios
import tty
from pathlib import Path

LIKED_DIR    = Path("labeled_data/liked")
DISLIKED_DIR = Path("labeled_data/disliked")
UNLABELED_DIR = Path("labeled_data/unlabeled")


def getch():
    """Read a single keypress without requiring Enter."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def open_image(path):
    """Open image in the system default viewer."""
    subprocess.Popen(
        ["xdg-open", str(path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def close_image_viewers():
    """Best-effort close of common image viewers after each photo."""
    for viewer in ["eog", "shotwell", "feh", "display", "xviewer"]:
        subprocess.run(["pkill", "-f", viewer],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def print_stats():
    liked    = len(list(LIKED_DIR.glob("*.png")))    if LIKED_DIR.exists()    else 0
    disliked = len(list(DISLIKED_DIR.glob("*.png"))) if DISLIKED_DIR.exists() else 0
    unlabeled = len(list(UNLABELED_DIR.glob("*.png"))) if UNLABELED_DIR.exists() else 0
    total = liked + disliked
    print(f"\n  Dataset stats")
    print(f"  ─────────────────────")
    print(f"  Liked:     {liked:>5}")
    print(f"  Disliked:  {disliked:>5}")
    print(f"  Total:     {total:>5}")
    if unlabeled:
        print(f"  Unlabeled: {unlabeled:>5}  (run without --review to label these)")
    if total > 0:
        balance = liked / total * 100
        print(f"  Balance:   {balance:.0f}% liked")
        if total >= 50:
            print(f"\n  Ready to train! Run: python train_classifier.py")
        else:
            print(f"\n  Need {50 - total} more samples before training.")
    print()


def label_batch(photos, source_label=None):
    """Label a list of photos interactively. source_label is 'liked'/'disliked' for review mode."""
    LIKED_DIR.mkdir(parents=True, exist_ok=True)
    DISLIKED_DIR.mkdir(parents=True, exist_ok=True)

    total = len(photos)
    if total == 0:
        print("No photos to label.")
        return

    print(f"\n  {total} photos to label.")
    print("  Controls: [y/Enter] = like  [n] = dislike  [s] = skip  [q] = quit\n")

    for i, photo in enumerate(photos):
        print(f"  [{i+1}/{total}] {photo.name}", end="  ", flush=True)
        open_image(photo)

        while True:
            key = getch().lower()

            if key in ("y", "\r", "\n", ""):
                dest = LIKED_DIR / photo.name
                if source_label == "liked":
                    print("→ keep LIKED")
                else:
                    shutil.move(str(photo), dest)
                    print("→ LIKED")
                break

            elif key == "n":
                dest = DISLIKED_DIR / photo.name
                if source_label == "disliked":
                    print("→ keep DISLIKED")
                elif source_label == "liked":
                    shutil.move(str(photo), DISLIKED_DIR / photo.name)
                    print("→ moved to DISLIKED")
                else:
                    shutil.move(str(photo), dest)
                    print("→ DISLIKED")
                break

            elif key == "s":
                if source_label is None:
                    UNLABELED_DIR.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(photo), UNLABELED_DIR / photo.name)
                print("→ skipped")
                break

            elif key == "q":
                close_image_viewers()
                print("\n\n  Quit. Progress saved.")
                print_stats()
                return

        close_image_viewers()

    print("\n  Done labeling this batch.")
    print_stats()


def main():
    parser = argparse.ArgumentParser(description="Label photos for CLIP training.")
    parser.add_argument("--review", action="store_true",
                        help="Re-review already labeled photos to fix mistakes.")
    parser.add_argument("--stats", action="store_true",
                        help="Show dataset statistics and exit.")
    parser.add_argument("--folder", type=str, default=None,
                        help="Label photos from a custom folder.")
    args = parser.parse_args()

    if args.stats:
        print_stats()
        return

    if args.folder:
        photos = sorted(Path(args.folder).glob("*.png"))
        label_batch(photos)
        return

    if args.review:
        print("\n  REVIEW MODE — fix existing labels")
        print("  ─────────────────────────────────")
        choice = input("  Review [l]iked, [d]isliked, or [b]oth? ").strip().lower()
        if choice in ("l", "b"):
            photos = sorted(LIKED_DIR.glob("*.png")) if LIKED_DIR.exists() else []
            print(f"\n  Reviewing {len(photos)} liked photos...")
            label_batch(photos, source_label="liked")
        if choice in ("d", "b"):
            photos = sorted(DISLIKED_DIR.glob("*.png")) if DISLIKED_DIR.exists() else []
            print(f"\n  Reviewing {len(photos)} disliked photos...")
            label_batch(photos, source_label="disliked")
        return

    # Default: label new photos collected by the bot that ended up in unlabeled/
    # or prompt for a source folder
    if UNLABELED_DIR.exists():
        photos = sorted(UNLABELED_DIR.glob("*.png"))
        if photos:
            print(f"\n  Found {len(photos)} unlabeled photos.")
            label_batch(photos)
            return

    print("\n  No unlabeled photos found.")
    print("  Run the bot to collect data, then come back here.")
    print("  Or use --folder <path> to label photos from a custom directory.")
    print_stats()


if __name__ == "__main__":
    main()
