"""HarvestService — scrapes profile data from the current screen.

Depends on ProfileStore for persistence. Accepts duck-typed `vision` and `adb`
objects so it works with any platform implementation — Meeff, Instagram, etc.
No bot-internal imports. Usable from any application that provides compatible
vision/adb objects.

Expected interface on `vision`:
    get_node_text(resource_id_suffix: str) -> str | None
    get_all_node_texts(resource_id_suffix: str) -> list[str]

Expected interface on `adb`:
    take_screenshot(crop_bounds=None) -> str | None   (returns local file path)
"""

import json
import os
import shutil
import time

from .store import ProfileStore


class HarvestService:
    """Scrapes and persists profile data from the active screen.

    Typical usage:

        harvest = HarvestService(store, vision, adb, platform="meeff")

        # In ProfileEvalTask after screenshot is taken:
        profile_id = harvest.harvest_profile(screenshot_path=path)
        harvest.record_decision(profile_id, liked=True)

        # In ChatTask when a message is sent/received:
        harvest.record_message(profile_id, direction="sent", text=reply)
    """

    # Resource-id suffixes used to read profile fields.
    # Override by subclassing if a platform uses different IDs.
    NAME_IDS    = ("nickname_textview", "name_textview")
    AGE_IDS     = ("age_textview",)
    BIO_IDS     = ("introduce_textview", "bio_textview", "description_textview", "purpose_textview")
    ANSWER_IDS  = ("answer_textview", "answer_content_textview")  # repeated Q&A nodes

    def __init__(
        self,
        store: ProfileStore,
        vision,
        adb,
        platform: str = "meeff",
    ) -> None:
        self._store = store
        self._vision = vision
        self._adb = adb
        self._platform = platform

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def harvest_profile(self, screenshot_path: str | None = None) -> str | None:
        """Read name/age/bio from the current screen and persist them.

        If `screenshot_path` is provided (already taken by the calling task),
        it is copied into the profile's photo directory and linked in the DB.

        Returns the profile_id string, or None if the name cannot be read
        (screen not ready / wrong state).
        """
        name = self._first_text(self.NAME_IDS)
        if not name:
            return None

        age_text = self._first_text(self.AGE_IDS)
        age = int(age_text) if age_text and age_text.isdigit() else None
        bio = self._first_text(self.BIO_IDS)
        answers = self._all_texts(self.ANSWER_IDS)

        profile_id = self._store.make_profile_id(name, age, self._platform)
        self._store.upsert(
            profile_id, self._platform,
            name=name, age=age, bio=bio,
            answers=json.dumps(answers, ensure_ascii=False) if answers else None,
        )

        if screenshot_path and os.path.exists(screenshot_path):
            dest = self._save_photo(profile_id, screenshot_path)
            self._store.add_photo(profile_id, dest)

        print(f"[Harvest] Profile saved: {name}, {age} → {profile_id}")
        return profile_id

    def record_decision(self, profile_id: str, liked: bool) -> None:
        """Persist the like/nope decision for a profile."""
        self._store.upsert(profile_id, self._platform, liked=int(liked))

    def record_message(self, profile_id: str, direction: str, text: str) -> None:
        """Append a chat message ('sent' or 'received') to the profile's history."""
        self._store.add_message(profile_id, direction, text)

    def harvest_chat_contact(self) -> str | None:
        """Look up or create a profile entry from the chat toolbar name.

        Called when ChatTask enters a conversation and needs a profile_id to
        link messages to. Only saves name — no photo or bio available here.
        Returns profile_id or None if the name cannot be read from the screen.
        """
        name = (
            self._vision.get_node_text("toolbar_title")
            or self._vision.get_node_text("title_textview")
            or self._vision.get_node_text("nickname_textview")
        )
        if not name:
            return None
        profile_id = self._store.make_profile_id(name, None, self._platform)
        self._store.upsert(profile_id, self._platform, name=name)
        return profile_id

    def get_profile(self, profile_id: str) -> dict | None:
        """Return the full profile dict for a given id, or None."""
        return self._store.get(profile_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _first_text(self, resource_id_suffixes: tuple[str, ...]) -> str | None:
        """Try each resource-id suffix in order; return the first non-empty text."""
        for suffix in resource_id_suffixes:
            text = self._vision.get_node_text(suffix)
            if text:
                return text
        return None

    def _all_texts(self, resource_id_suffixes: tuple[str, ...]) -> list[str]:
        """Collect all text values across all nodes matching any of the given suffixes."""
        seen, results = set(), []
        for suffix in resource_id_suffixes:
            for text in self._vision.get_all_node_texts(suffix):
                if text not in seen:
                    seen.add(text)
                    results.append(text)
        return results

    def _save_photo(self, profile_id: str, src_path: str) -> str:
        """Copy a photo into data/photos/{profile_id}/ and return the dest path."""
        dest_dir = os.path.join("data", "photos", profile_id)
        os.makedirs(dest_dir, exist_ok=True)
        ext = os.path.splitext(src_path)[1] or ".jpg"
        dest = os.path.join(dest_dir, f"{int(time.time())}{ext}")
        shutil.copy(src_path, dest)
        return dest
