#!/usr/bin/env python3
"""Quick viewer for the profile database.

Usage:
    python show_profiles.py                   # list all profiles
    python show_profiles.py <profile_id>      # full detail by exact ID
    python show_profiles.py --search <name>   # fuzzy search by name
"""

import argparse
import difflib
import json
import sys
from datetime import datetime

from profile_db import ProfileStore

DB_PATH = "data/profiles.db"
SEP = "─" * 62


def fmt_time(ts: float | None) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def fmt_liked(value) -> str:
    if value is None:
        return "?"
    return "liked" if value else "noped"


# ------------------------------------------------------------------
# Views
# ------------------------------------------------------------------

def list_all(store: ProfileStore) -> None:
    rows = store._conn.execute(
        "SELECT id, platform, name, age, liked, first_seen, last_seen"
        " FROM profiles ORDER BY last_seen DESC"
    ).fetchall()

    if not rows:
        print("No profiles saved yet.")
        return

    print(f"\n{'ID':<18} {'PLATFORM':<10} {'NAME':<20} {'AGE':<5} {'DECISION':<8} LAST SEEN")
    print(SEP)
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
    print(f"  ID        : {profile['id']}")
    print(f"  Platform  : {profile['platform']}")
    print(f"  Name      : {profile['name'] or '—'}")
    print(f"  Age       : {profile['age'] or '—'}")
    print(f"  Bio       : {profile['bio'] or '—'}")
    print(f"  Decision  : {fmt_liked(profile['liked'])}")
    print(f"  First seen: {fmt_time(profile['first_seen'])}")
    print(f"  Last seen : {fmt_time(profile['last_seen'])}")

    answers = []
    if profile.get("answers"):
        try:
            answers = json.loads(profile["answers"])
        except (json.JSONDecodeError, TypeError):
            pass

    print(f"\n  Q&A Answers ({len(answers)}):")
    if answers:
        for i, ans in enumerate(answers, 1):
            print(f"    {i}. {ans}")
    else:
        print("    none")

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


def search_by_name(store: ProfileStore, query: str) -> None:
    rows = store._conn.execute(
        "SELECT id, platform, name, age, liked, last_seen"
        " FROM profiles WHERE name IS NOT NULL"
    ).fetchall()

    if not rows:
        print("No profiles saved yet.")
        return

    # Score each profile: exact substring first, then difflib similarity
    scored = []
    q = query.lower()
    for r in rows:
        name = (r["name"] or "").lower()
        if q in name:
            score = 1.0 + len(q) / max(len(name), 1)  # longer match = higher score
        else:
            score = difflib.SequenceMatcher(None, q, name).ratio()
        scored.append((score, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    matches = [(s, r) for s, r in scored if s >= 0.4]

    if not matches:
        print(f"No profiles found matching '{query}'.")
        return

    print(f"\nSearch results for '{query}':\n")
    print(f"{'SCORE':<7} {'ID':<18} {'PLATFORM':<10} {'NAME':<20} {'AGE':<5} {'DECISION':<8} LAST SEEN")
    print(SEP)
    for score, r in matches:
        print(
            f"{score:<7.2f} {r['id']:<18} {r['platform']:<10} {(r['name'] or '?'):<20}"
            f" {(str(r['age']) if r['age'] else '?'):<5}"
            f" {fmt_liked(r['liked']):<8} {fmt_time(r['last_seen'])}"
        )
    print(f"\n{len(matches)} match(es). Use the ID to see full details:")
    print(f"  python show_profiles.py <id>")


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Profile database viewer")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("profile_id", nargs="?", help="Show full detail for this profile ID")
    group.add_argument("--search", "-s", metavar="NAME", help="Fuzzy search by name")
    args = parser.parse_args()

    store = ProfileStore(DB_PATH)
    try:
        if args.search:
            search_by_name(store, args.search)
        elif args.profile_id:
            show_detail(store, args.profile_id)
        else:
            list_all(store)
    finally:
        store.close()


if __name__ == "__main__":
    main()
