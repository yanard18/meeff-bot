import re
import time

from ..core.platform import Platform, MatchedFriend, LikedProfile, ChatCandidate
from ..core.states import (
    NOT_OPENED, UNKNOWN_FAILED,
    QUIT_DIALOG, SUGGEST_MEEFF, MATCH_COMPLETE, AD, NATIVE_AD,
    MATCHED_FRIEND_PROFILE, DETAILED_PROFILE, SWIPE_MODE, FIND_PAGE,
    CHAT_WITH_PERSON, CHAT_LIST, MY_PROFILE, SEARCH_FILTERS,
    LIKE_VISITOR_PAGE, TODAY_PAGE, UNKNOWN_SCREEN,
)
from ..adb_service import AdbService
from ..vision_service import VisionService

_PACKAGE = "com.noyesrun.meeff.kr"

# resource-id suffixes that identify each screen
_SCREEN_FINGERPRINTS = [
    # Dialogs — checked first because they overlay other screens
    (QUIT_DIALOG,            lambda ids, _: 'messageTextView' in ids and 'negativeButton' in ids),
    (SUGGEST_MEEFF,          lambda ids, _: 'md_root' in ids),
    (MATCH_COMPLETE,         lambda ids, _: 'target_photo_imageview' in ids),
    (AD,                     lambda _, ds: 'Ad closed' in ds or 'Close ad' in ds),
    (NATIVE_AD,              lambda ids, _: 'native_ad_conatiner' in ids),  # typo is in the app
    # Content screens
    (MATCHED_FRIEND_PROFILE, lambda ids, _: 'open_chat_layout' in ids),
    (DETAILED_PROFILE,       lambda ids, _: 'force_open_imageview' in ids or 'answer_layout' in ids),
    (SWIPE_MODE,             lambda ids, _: 'action_layout' in ids or 'like_imageview' in ids),
    (FIND_PAGE,              lambda ids, _: 'voice_bloom_imageview' in ids or 'vibe_meet_imageview' in ids),
    (CHAT_WITH_PERSON,       lambda ids, _: 'message_edittext' in ids or 'send_imageview' in ids),
    (CHAT_LIST,              lambda ids, _: 'last_msg_textview' in ids or 'local_time_textview' in ids),
    (MY_PROFILE,             lambda ids, _: 'plus_layout' in ids or 'ruby_count_textview' in ids),
    (SEARCH_FILTERS,         lambda ids, _: 'distance_seekbar' in ids),
    (LIKE_VISITOR_PAGE,      lambda ids, _: 'option_imageview' in ids or 'no_result_title_textview' in ids),
    (TODAY_PAGE,             lambda ids, _: 'refresh_layout' in ids),
]

_NAME_IDS    = {'nickname_textview', 'name_textview', 'user_name_textview', 'title_textview'}
_UNREAD_IDS  = {'unread_count_textview', 'badge_count_textview',
                'new_message_count_textview', 'unread_textview'}
_OPENED_CHAT = "has opened the chat room"


class MeeffPlatform(Platform):
    """Meeff-specific UI adapter.

    All Meeff resource-id knowledge lives here. Tasks call only the abstract
    Platform methods; zero task code changes are needed to add Instagram support
    — just write an InstagramPlatform subclass.
    """

    def __init__(self, adb: AdbService, vision: VisionService) -> None:
        self._adb = adb
        self._vision = vision

    # ------------------------------------------------------------------
    # Platform interface
    # ------------------------------------------------------------------

    @property
    def app_package(self) -> str:
        return _PACKAGE

    def detect_state(self) -> str:
        """Refresh UI dump and fingerprint the current screen."""
        if not self._vision.refresh_screen_data():
            return UNKNOWN_FAILED

        if not self._is_app_open():
            return NOT_OPENED

        res_ids = self._vision.collect_resource_ids()
        descs   = self._vision.collect_content_descs()

        for state, test in _SCREEN_FINGERPRINTS:
            if test(res_ids, descs):
                return state

        return UNKNOWN_SCREEN

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
        like_tab = self._get_like_inner_tab_bounds()
        if like_tab:
            self._adb.human_tap(like_tab, name="Like Tab")
            time.sleep(1.5)

    def get_matched_friends(self) -> list[MatchedFriend]:
        return [MatchedFriend(bounds=card['bounds'])
                for card in self._get_all_matched_friend_cards()]

    def get_liked_profiles(self) -> list[LikedProfile]:
        bounds = self._vision.get_node_bounds('thumb_photo_imageview')
        return [LikedProfile(bounds=bounds)] if bounds else []

    def get_chat_candidates(self) -> list[ChatCandidate]:
        candidates: dict[str, ChatCandidate] = {}

        # Matched friends (time-limited — highest priority).
        # Key per card so multiple matched friends are distinct.
        for i, card in enumerate(self._get_all_matched_friend_cards()):
            name = card['name'] or f"Matched Friend {i + 1}"
            key = f"__matched_{i}__"
            candidates[key] = ChatCandidate(
                name=name,
                bounds=card['bounds'],
                has_unread=False,
                is_matched=True,
            )

        # Chat rows with unread messages or "opened chat room" notices
        for row in self._get_chat_list_rows():
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

    # ------------------------------------------------------------------
    # Meeff-specific UI queries (private — tasks never call these)
    # ------------------------------------------------------------------

    def _find_clickable_ancestor(self, node, parent_map: dict, max_depth: int = 6):
        """Walk up parent_map until a clickable ancestor is found or depth is exhausted."""
        container = node
        for _ in range(max_depth):
            p = parent_map.get(container)
            if p is None:
                break
            container = p
            if container.attrib.get('clickable') == 'true':
                break
        return container

    def _is_app_open(self) -> bool:
        """True if any node in the current tree belongs to the Meeff package."""
        if self._vision.cached_tree is None:
            return False
        for node in self._vision.cached_tree.iter('node'):
            if node.attrib.get('package') == _PACKAGE:
                return True
        return False

    def _get_like_inner_tab_bounds(self) -> dict | None:
        """Bounds of the 'Like' inner tab within the Chat/Dashboard section."""
        if self._vision.cached_tree is None:
            return None
        for node in self._vision.cached_tree.iter('node'):
            if node.attrib.get('clickable') != 'true':
                continue
            for child in node.iter('node'):
                if (child.attrib.get('text') == 'Like' and
                        'title_textview' in child.attrib.get('resource-id', '')):
                    bounds = self._vision._parse_bounds(node)
                    if bounds and bounds['y_min'] < 300:
                        return bounds
        return None

    def _get_all_matched_friend_cards(self) -> list[dict]:
        """All matched friend cards visible in the horizontal carousel.

        Each dict: {bounds, name}.  expire_progressbar is the unique fingerprint
        for matched-friend cards. Walks up to the clickable container.
        """
        if self._vision.cached_tree is None:
            return []

        parent_map = self._vision.build_parent_map()
        _CARD_NAME_IDS = {'nickname_textview', 'name_textview', 'user_name_textview'}
        cards = []
        seen: set[tuple] = set()

        for node in self._vision.cached_tree.iter('node'):
            if node.attrib.get('resource-id', '').split('/')[-1] != 'expire_progressbar':
                continue

            container = self._find_clickable_ancestor(node, parent_map)

            bounds = self._vision._parse_bounds(container) or self._vision._parse_bounds(node)
            if not bounds:
                continue

            key = (bounds['x_min'], bounds['y_min'])
            if key in seen:
                continue
            seen.add(key)

            name = ""
            for child in container.iter('node'):
                if child.attrib.get('resource-id', '').split('/')[-1] in _CARD_NAME_IDS:
                    text = child.attrib.get('text', '').strip()
                    if text:
                        name = text
                        break

            cards.append({'bounds': bounds, 'name': name})

        return cards

    def _get_chat_list_rows(self) -> list[dict]:
        """All visible conversation rows on the chat list screen.

        Each dict: {name, bounds, has_unread, last_msg}.
        """
        if self._vision.cached_tree is None:
            return []

        parent_map = self._vision.build_parent_map()
        rows = []
        seen: set[tuple] = set()

        for node in self._vision.cached_tree.iter('node'):
            if node.attrib.get('resource-id', '').split('/')[-1] != 'last_msg_textview':
                continue

            container = self._find_clickable_ancestor(node, parent_map)

            if container.attrib.get('clickable') != 'true':
                continue

            bounds = self._vision._parse_bounds(container)
            if not bounds:
                continue

            key = (bounds['x_min'], bounds['y_min'])
            if key in seen:
                continue
            seen.add(key)

            last_msg = node.attrib.get('text', '').strip()

            name = None
            for child in container.iter('node'):
                if child.attrib.get('resource-id', '').split('/')[-1] in _NAME_IDS:
                    text = child.attrib.get('text', '').strip()
                    if text:
                        name = text
                        break

            has_unread = any(
                child.attrib.get('resource-id', '').split('/')[-1] in _UNREAD_IDS
                and child.attrib.get('text', '').strip() not in ('', '0')
                for child in container.iter('node')
            )

            if name:
                rows.append({
                    'name': name,
                    'bounds': bounds,
                    'has_unread': has_unread,
                    'last_msg': last_msg,
                })

        return rows

    def get_like_count(self) -> int:
        """Number of incoming likes shown on the Like tab page."""
        if self._vision.cached_tree is None:
            return 0
        for node in self._vision.cached_tree.iter('node'):
            m = re.match(r'^(\d+)\s+Friend', node.attrib.get('text', ''))
            if m:
                return int(m.group(1))
        return 0

    def get_matched_friends_count(self) -> int:
        """Number of matched friends shown in the chat list."""
        if self._vision.cached_tree is None:
            return 0
        for node in self._vision.cached_tree.iter('node'):
            m = re.match(r'^(\d+)\s+matched friend', node.attrib.get('text', ''))
            if m:
                return int(m.group(1))
        return 0
