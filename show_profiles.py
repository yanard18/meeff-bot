#!/usr/bin/env python3
"""Quick viewer for the profile database.

Usage:
    python show_profiles.py              # list all profiles
    python show_profiles.py <profile_id> # full detail for one profile
"""

import sys
from datetime import datetime
from profile_db import ProfileStore

DB_PATH = "data/profiles.db"
SEP = "-" * 60


def fmt_time(ts: float | None) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def fmt_liked(value) -> str:
    if value is None:
        return "?"
    return "liked" if value else "noped"


def list_all(store: ProfileStore) -> None:
    rows = store._conn.execute(
        "SELECT id, platform, name, age, liked, first_seen, last_seen"
        " FROM profiles ORDER BY last_seen DESC"
    ).fetchall()

    if not rows:
        print("No profiles saved yet.")
        return

    print(f"\n{'ID':<18} {'PLATFORM':<10} {'NAME':<20} {'AGE':<5} {'DECISION':<8} {'LAST SEEN'}")
    print(SEP + SEP[:20])
    for r in rows:
        print(
            f"{r['id']:<18} {r['platform']:<10} {(r['name'] or '?'):<20}"
            f" {(str(r['age']) if r['age'] else '?'):<5}"
            f" {fmt_liked(r['liked']):<8} {fmt_time(r['last_seen'])}"
        )
    print(f"\n{len(rows)} profile(s) total.")


def show_detail(store: ProfileStore, profile_id: str) -> None:
    profile = store.get(profile_id)
    if not profile:
        print(f"No profile found with id: {profile_id}")
        return

    print(f"\n{SEP}")
    print(f"  ID       : {profile['id']}")
    print(f"  Platform : {profile['platform']}")
    print(f"  Name     : {profile['name'] or '—'}")
    print(f"  Age      : {profile['age'] or '—'}")
    print(f"  Bio      : {profile['bio'] or '—'}")
    print(f"  Decision : {fmt_liked(profile['liked'])}")
    print(f"  First seen: {fmt_time(profile['first_seen'])}")
    print(f"  Last seen : {fmt_time(profile['last_seen'])}")

    photos = profile["photos"]
    print(f"\n  Photos ({len(photos)}):")
    if photos:
        for p in photos:
            print(f"    {p}")
    else:
        print("    none")

    messages = profile["messages"]
    print(f"\n  Chat history ({len(messages)} messages):")
    if messages:
        for m in messages:
            arrow = "→" if m["direction"] == "sent" else "←"
            print(f"    [{fmt_time(m['timestamp'])}] {arrow} {m['text']}")
    else:
        print("    none")

    print(SEP)


def main() -> None:
    store = ProfileStore(DB_PATH)
    try:
        if len(sys.argv) > 1:
            show_detail(store, sys.argv[1])
        else:
            list_all(store)
    finally:
        store.close()


if __name__ == "__main__":
    main()
