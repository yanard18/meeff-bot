#!/usr/bin/env python3
"""
Screenshot integration test.

Verifies that the ADB screenshot pipeline works end-to-end.
Saves files to screenshots/ so you can inspect them visually.

Run with phone connected and Meeff open on a DETAILED PROFILE:
    python test_screenshot.py
"""
import os
import sys
import struct
import subprocess
import time
from PIL import Image, ImageStat


SAVE_DIR = "screenshots"


def _is_all_black(img):
    stat = ImageStat.Stat(img.convert("RGB"))
    return all(m < 2 for m in stat.mean)


def _take_png(save_path):
    """Pull method: screencap -p on device, then adb pull."""
    r = subprocess.run(
        ['adb', 'shell', 'screencap', '-p', '/sdcard/_test_shot.png'],
        capture_output=True, timeout=10
    )
    if r.returncode != 0:
        return None, f"screencap failed (rc={r.returncode})"

    r2 = subprocess.run(
        ['adb', 'pull', '/sdcard/_test_shot.png', save_path],
        capture_output=True, timeout=10
    )
    if r2.returncode != 0 or not os.path.exists(save_path):
        return None, "adb pull failed"

    img = Image.open(save_path)
    return img, None


def _take_raw_rgba(save_path):
    """exec-out method: raw RGBA stream, no -p flag.
    Sometimes bypasses FLAG_SECURE on certain devices."""
    r = subprocess.run(
        ['adb', 'exec-out', 'screencap'],
        capture_output=True, timeout=10
    )
    if r.returncode != 0 or len(r.stdout) < 12:
        return None, "exec-out screencap returned no data"

    data = r.stdout
    width  = struct.unpack_from('<I', data, 0)[0]
    height = struct.unpack_from('<I', data, 4)[0]
    pixel_data = data[12:]
    expected = width * height * 4

    if len(pixel_data) != expected:
        return None, f"data size mismatch: got {len(pixel_data)}, expected {expected}"

    img = Image.frombytes('RGBA', (width, height), pixel_data)
    img.save(save_path)
    return img, None


def _report(label, save_path, img, err):
    print(f"  Method : {label}")
    if err or img is None:
        print(f"  Result : FAIL — {err}")
        print()
        return

    size_kb   = os.path.getsize(save_path) / 1024
    all_black = _is_all_black(img)

    print(f"  File   : {save_path}")
    print(f"  Size   : {size_kb:.1f} KB  (real app screen is usually 200–600 KB)")
    print(f"  Dims   : {img.width}x{img.height}  mode={img.mode}")

    if all_black:
        print(f"  Result : FAIL — image is all black")
        print(f"  Cause  : Meeff has FLAG_SECURE set. Android 15 enforces this for")
        print(f"           ADB screencap. AI scoring will fall back to 'always like'.")
    else:
        stat = ImageStat.Stat(img.convert("RGB"))
        print(f"  Pixels : mean RGB = {[round(m, 1) for m in stat.mean[:3]]}")
        print(f"  Result : OK — screenshot has real content, AI scoring will work")
    print()


def main():
    os.makedirs(SAVE_DIR, exist_ok=True)
    ts = int(time.time())

    print("\n=== Screenshot Pipeline Test ===")
    print("(open Meeff on a detailed profile before running for best results)\n")

    # ── 1. ADB check ────────────────────────────────────────────────────────
    r = subprocess.run(['adb', 'get-state'], capture_output=True, text=True)
    connected = r.stdout.strip() == 'device'
    print(f"  ADB device : {'connected' if connected else 'NOT FOUND'}")
    if not connected:
        print("  Connect your phone and re-run.")
        sys.exit(1)

    # ── 2. PNG method ────────────────────────────────────────────────────────
    png_path = os.path.join(SAVE_DIR, f"test_png_{ts}.png")
    img, err = _take_png(png_path)
    _report("screencap -p  (standard)", png_path, img, err)

    # ── 3. Raw RGBA method ───────────────────────────────────────────────────
    raw_path = os.path.join(SAVE_DIR, f"test_raw_{ts}.png")
    img, err = _take_raw_rgba(raw_path)
    _report("exec-out raw RGBA (fallback)", raw_path, img, err)

    # ── 4. Summary ───────────────────────────────────────────────────────────
    png_ok = os.path.exists(png_path) and not _is_all_black(Image.open(png_path))
    raw_ok = os.path.exists(raw_path) and not _is_all_black(Image.open(raw_path))

    print("=== Summary ===")
    if png_ok or raw_ok:
        print("  Screenshots work — AI photo scoring is fully operational.")
    else:
        print("  Both methods produce black images (FLAG_SECURE).")
        print("  AI scoring is blocked by the app. The bot will default to liking all profiles.")
        print("  This is a device/OS-level restriction, not a code bug.")
    print()


if __name__ == '__main__':
    main()
