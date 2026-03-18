#!/usr/bin/env python3
"""
UI capture tool — dumps the current screen's XML hierarchy to page_data/.

Usage:
    python capture_page.py <name>

Example:
    python capture_page.py likes_tab_with_badge
    python capture_page.py likes_grid
    python capture_page.py likes_profile_view
"""

import sys
from pathlib import Path
from src.adb_service import AdbService


def main():
    if len(sys.argv) < 2:
        print("Usage: python capture_page.py <name>")
        sys.exit(1)

    name = sys.argv[1]
    out_path = Path("page_data") / f"{name}.xml"

    adb = AdbService()
    print(f"[Capture] Dumping UI hierarchy...")
    xml = adb.get_window_dump()

    if not xml:
        print("[Capture] Failed to get UI dump. Is the device connected?")
        sys.exit(1)

    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(xml, encoding="utf-8")
    print(f"[Capture] Saved → {out_path}")


if __name__ == "__main__":
    main()
