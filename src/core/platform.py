from abc import ABC, abstractmethod


class Platform(ABC):
    """Abstract interface for a target app platform (Meeff, Instagram, …).

    Decouples task logic from UI fingerprints: tasks express *intent*,
    platforms express *how to detect and navigate* a specific app's UI.
    """

    @property
    @abstractmethod
    def app_package(self) -> str:
        """Android package name, e.g. 'com.noyesrun.meeff.kr'."""

    @abstractmethod
    def detect_state(self) -> str:
        """Return a human-readable string describing the current UI state.

        The returned string is passed verbatim to Task.is_eligible() so tasks
        can match it however they like (substring, equality, regex, …).
        """
