import time

from ..core.platform import Platform, MatchedFriend, LikedProfile, ChatCandidate
from ..adb_service import AdbService
from ..vision_service import VisionService


class MeeffPlatform(Platform):
    """Meeff-specific UI adapter.

    All Meeff resource-id knowledge lives here. Tasks call semantic methods
    like navigate_to_chat_list() and never touch resource-ids directly,
    so no task code changes when Instagram support is added.
    """

    def __init__(self, adb: AdbService, vision: VisionService) -> None:
        self._adb = adb
        self._vision = vision

    @property
    def app_package(self) -> str:
        return "com.noyesrun.meeff.kr"

    def detect_state(self) -> str:
        return self._vision.determine_app_state()

    def navigate_to_swipe(self) -> None:
        self._vision.refresh_screen_data()
        tab = self._vision.get_node_bounds("tab_explore")
        if tab:
            self._adb.human_tap(tab, name="Swipe Tab")
            time.sleep(1.5)

    def navigate_to_chat_list(self) -> None:
        self._vision.refresh_screen_data()
        tab = self._vision.get_node_bounds("tab_dashboard")
        if tab:
            self._adb.human_tap(tab, name="Chat Tab")
            time.sleep(1.5)

    def navigate_to_likes(self) -> None:
        like_tab = self._vision.get_like_inner_tab_bounds()
        if like_tab:
            self._adb.human_tap(like_tab, name="Like Tab")
            time.sleep(1.5)

    def get_matched_friends(self) -> list[MatchedFriend]:
        bounds = self._vision.get_first_matched_friend_bounds()
        return [MatchedFriend(bounds=bounds)] if bounds else []

    def get_liked_profiles(self) -> list[LikedProfile]:
        bounds = self._vision.get_first_liked_profile_bounds()
        return [LikedProfile(bounds=bounds)] if bounds else []

    def get_chat_candidates(self) -> list[ChatCandidate]:
        candidates: dict[str, ChatCandidate] = {}

        # Matched friends (time-limited — highest priority)
        if self._vision.get_first_matched_friend_bounds():
            bounds = self._vision.get_first_matched_friend_bounds()
            # Name not easily extractable from matched card; use placeholder
            candidates["__matched__"] = ChatCandidate(
                name="Matched Friend",
                bounds=bounds,
                has_unread=False,
                is_matched=True,
            )

        _OPENED_CHAT = "has opened the chat room"

        # Chat rows with unread messages or "opened chat room" system messages
        for row in self._vision.get_chat_list_rows():
            name = row["name"]
            has_action = row["has_unread"] or _OPENED_CHAT in row.get("last_msg", "")
            if name not in candidates and has_action:
                candidates[name] = ChatCandidate(
                    name=name,
                    bounds=row["bounds"],
                    has_unread=has_action,
                    is_matched=False,
                )

        return list(candidates.values())
