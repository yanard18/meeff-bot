import time

from ..core.platform import Platform, MatchedFriend, LikedProfile
from ..adb_service import AdbService
from ..vision_service import VisionService


class MeeffPlatform(Platform):
    """Meeff-specific UI adapter.

    All Meeff resource-id knowledge lives here. Tasks call semantic methods
    like navigate_to_chat_list() and never touch resource-ids directly,
    so no task code changes when Instagram support is added.
    """

    def __init__(self, adb: AdbService, vision: VisionService) -> None:
        self._adb    = adb
        self._vision = vision

    @property
    def app_package(self) -> str:
        return "com.noyesrun.meeff.kr"

    # ------------------------------------------------------------------
    # State detection
    # ------------------------------------------------------------------

    def detect_state(self) -> str:
        return self._vision.determine_app_state()

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Chat list queries
    # ------------------------------------------------------------------

    def get_matched_friends(self) -> list[MatchedFriend]:
        count = self._vision.get_matched_friends_count()
        if count == 0:
            return []
        bounds = self._vision.get_first_matched_friend_bounds()
        if bounds:
            return [MatchedFriend(bounds=bounds)]
        return []

    def get_liked_profiles(self) -> list[LikedProfile]:
        count = self._vision.get_like_count()
        if count == 0:
            return []
        bounds = self._vision.get_first_liked_profile_bounds()
        if bounds:
            return [LikedProfile(bounds=bounds)]
        return []
