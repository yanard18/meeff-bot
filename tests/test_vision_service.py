import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.vision_service import VisionService
from src.platforms.meeff import MeeffPlatform
from src.core import states


class MockAdbService:
    """Fake AdbService that returns static XML instead of talking to a device."""

    def __init__(self, mock_xml_content):
        self.mock_xml_content = mock_xml_content

    def get_window_dump(self):
        return self.mock_xml_content

    def get_screen_width(self):
        return 1080

    def is_device_connected(self):
        return True

    def is_device_awake(self):
        return True


def _platform_for(xml_content: str) -> MeeffPlatform:
    adb = MockAdbService(xml_content)
    vision = VisionService(adb)
    return MeeffPlatform(adb, vision)


class TestMeeffStateDetection(unittest.TestCase):
    def load_xml(self, filename: str) -> str:
        path = os.path.join(os.path.dirname(__file__), '..', 'page_data', filename)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def test_swipe_page_detection(self):
        platform = _platform_for(self.load_xml("swipe_page.xml"))
        self.assertEqual(platform.detect_state(), states.SWIPE_MODE)

    def test_chat_list_detection(self):
        platform = _platform_for(self.load_xml("chat_page.xml"))
        self.assertEqual(platform.detect_state(), states.CHAT_LIST)

    def test_find_page_detection(self):
        platform = _platform_for(self.load_xml("find_page.xml"))
        self.assertEqual(platform.detect_state(), states.FIND_PAGE)

    def test_my_profile_detection(self):
        platform = _platform_for(self.load_xml("my_profile.xml"))
        self.assertEqual(platform.detect_state(), states.MY_PROFILE)

    def test_search_filters_detection(self):
        platform = _platform_for(self.load_xml("search_filters.xml"))
        self.assertEqual(platform.detect_state(), states.SEARCH_FILTERS)

    def test_like_page_detection(self):
        platform = _platform_for(self.load_xml("like_page.xml"))
        self.assertEqual(platform.detect_state(), states.LIKE_VISITOR_PAGE)

    def test_today_page_detection(self):
        platform = _platform_for(self.load_xml("today_page.xml"))
        self.assertEqual(platform.detect_state(), states.TODAY_PAGE)

    def test_detailed_profile_detection(self):
        platform = _platform_for(self.load_xml("detailed_profile.xml"))
        self.assertEqual(platform.detect_state(), states.DETAILED_PROFILE)

    def test_chat_with_person_detection(self):
        platform = _platform_for(self.load_xml("chat_with_person.xml"))
        self.assertEqual(platform.detect_state(), states.CHAT_WITH_PERSON)


if __name__ == "__main__":
    unittest.main()
