from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class MatchedFriend:
    bounds: dict


@dataclass
class LikedProfile:
    bounds: dict


class Platform(ABC):
    """Abstract interface for a target app platform (Meeff, Instagram, …).

    Two responsibilities:
      1. State detection  — what screen are we on?
      2. Semantic navigation — how do we get somewhere / query the UI?

    Tasks call only these methods, never vision_service directly.
    Swapping MeeffPlatform for InstagramPlatform requires zero task changes.
    """

    @property
    @abstractmethod
    def app_package(self) -> str:
        """Android package name, e.g. 'com.noyesrun.meeff.kr'."""

    @abstractmethod
    def detect_state(self) -> str:
        """Return a string describing the current UI state.

        Passed verbatim to Task.is_eligible(), so tasks can match it however
        they like (substring, equality, regex, …).
        """

    @abstractmethod
    def navigate_to_swipe(self) -> None:
        """Go to the main profile-swiping screen."""

    @abstractmethod
    def navigate_to_chat_list(self) -> None:
        """Go to the inbox / chat list screen."""

    @abstractmethod
    def navigate_to_likes(self) -> None:
        """Go to the incoming-likes / visitor screen."""

    @abstractmethod
    def get_matched_friends(self) -> list[MatchedFriend]:
        """Return all matched friends currently visible on the chat list."""

    @abstractmethod
    def get_liked_profiles(self) -> list[LikedProfile]:
        """Return all profiles that liked us, visible on the likes page."""
