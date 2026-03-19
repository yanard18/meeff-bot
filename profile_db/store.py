"""ProfileStore — SQLite-backed persistence for harvested profiles.

Completely standalone: no bot dependencies. Import it from any application:

    from profile_db import ProfileStore

    store = ProfileStore("data/profiles.db")
    store.upsert(profile_id, "meeff", name="Alice", age=25)
    store.add_photo(profile_id, "data/photos/abc123/1234567890.jpg")
    print(store.get(profile_id))
    store.close()
"""

import hashlib
import os
import sqlite3
import time

# Only these columns may be set via upsert() — prevents accidental schema bypass.
_UPDATABLE_FIELDS = frozenset({"name", "age", "bio", "liked"})

_SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    id          TEXT    PRIMARY KEY,
    platform    TEXT    NOT NULL,
    name        TEXT,
    age         INTEGER,
    bio         TEXT,
    liked       INTEGER,            -- 1=liked, 0=noped, NULL=unknown
    first_seen  REAL    NOT NULL,
    last_seen   REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS photos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id  TEXT    NOT NULL REFERENCES profiles(id),
    path        TEXT    NOT NULL,
    taken_at    REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id  TEXT    NOT NULL REFERENCES profiles(id),
    direction   TEXT    NOT NULL,   -- "sent" or "received"
    text        TEXT    NOT NULL,
    timestamp   REAL    NOT NULL
);
"""


class ProfileStore:
    """SQLite-backed store for profile data, photos, and chat history.

    Thread-safe for single-writer use (check_same_thread=False).
    All writes are committed immediately — no transaction management needed
    at this scale.
    """

    def __init__(self, db_path: str = "data/profiles.db") -> None:
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Profile ID generation
    # ------------------------------------------------------------------

    @staticmethod
    def make_profile_id(name: str, age: int | None, platform: str) -> str:
        """Deterministic 16-char ID from name + age + platform.

        The same person seen again on the same platform resolves to the same
        row, so data accumulates rather than duplicates.
        """
        key = f"{platform}:{name.lower()}:{age or ''}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def upsert(self, profile_id: str, platform: str, **fields) -> None:
        """Insert or update a profile row.

        Only keys in _UPDATABLE_FIELDS are accepted; unknown keys are ignored.
        `first_seen` is set on insert and never updated. `last_seen` is always
        refreshed.
        """
        safe_fields = {k: v for k, v in fields.items() if k in _UPDATABLE_FIELDS}
        now = time.time()

        existing = self._conn.execute(
            "SELECT id FROM profiles WHERE id = ?", (profile_id,)
        ).fetchone()

        if existing:
            if safe_fields:
                set_clause = ", ".join(f"{k} = ?" for k in safe_fields)
                self._conn.execute(
                    f"UPDATE profiles SET {set_clause}, last_seen = ? WHERE id = ?",
                    [*safe_fields.values(), now, profile_id],
                )
            else:
                self._conn.execute(
                    "UPDATE profiles SET last_seen = ? WHERE id = ?",
                    (now, profile_id),
                )
        else:
            cols = ["id", "platform", "first_seen", "last_seen", *safe_fields]
            placeholders = ", ".join("?" * len(cols))
            self._conn.execute(
                f"INSERT INTO profiles ({', '.join(cols)}) VALUES ({placeholders})",
                [profile_id, platform, now, now, *safe_fields.values()],
            )

        self._conn.commit()

    def add_photo(self, profile_id: str, path: str) -> None:
        """Record a photo path linked to a profile."""
        self._conn.execute(
            "INSERT INTO photos (profile_id, path, taken_at) VALUES (?, ?, ?)",
            (profile_id, path, time.time()),
        )
        self._conn.commit()

    def add_message(self, profile_id: str, direction: str, text: str) -> None:
        """Append a chat message. direction must be 'sent' or 'received'."""
        self._conn.execute(
            "INSERT INTO chat_messages (profile_id, direction, text, timestamp)"
            " VALUES (?, ?, ?, ?)",
            (profile_id, direction, text, time.time()),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get(self, profile_id: str) -> dict | None:
        """Return full profile dict with photos and messages, or None."""
        row = self._conn.execute(
            "SELECT * FROM profiles WHERE id = ?", (profile_id,)
        ).fetchone()
        if not row:
            return None

        result = dict(row)
        result["photos"] = [
            r["path"]
            for r in self._conn.execute(
                "SELECT path FROM photos WHERE profile_id = ? ORDER BY taken_at",
                (profile_id,),
            ).fetchall()
        ]
        result["messages"] = [
            dict(r)
            for r in self._conn.execute(
                "SELECT direction, text, timestamp FROM chat_messages"
                " WHERE profile_id = ? ORDER BY timestamp",
                (profile_id,),
            ).fetchall()
        ]
        return result

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        self._conn.close()
