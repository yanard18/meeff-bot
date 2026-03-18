import unittest
import os
import sys

# Ensure we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.vision_service import VisionService

class MockAdbService:
    """A fake AdbService that returns static XML strings instead of talking to a phone."""
    def __init__(self, mock_xml_content):
        self.mock_xml_content = mock_xml_content

    def get_window_dump(self):
        return self.mock_xml_content
    
    # Mocking other methods that might be called, though VisionService mainly needs get_window_dump
    def is_device_connected(self):
        return True
    
    def is_device_awake(self):
        return True

class TestVisionService(unittest.TestCase):
    def load_xml(self, filename):
        """Helper to load XML files from the page_data directory."""
        path = os.path.join(os.path.dirname(__file__), '..', 'page_data', filename)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def test_swipe_page_detection(self):
        xml_content = self.load_xml("swipe_page.xml")
        adb = MockAdbService(xml_content)
        vision = VisionService(adb)
        self.assertEqual(vision.determine_app_state(), "ACTIVE (Swipe Mode)")

    def test_chat_page_detection(self):
        xml_content = self.load_xml("chat_page.xml")
        adb = MockAdbService(xml_content)
        vision = VisionService(adb)
        self.assertEqual(vision.determine_app_state(), "ACTIVE (Chat List)")
        
    def test_find_page_detection(self):
        xml_content = self.load_xml("find_page.xml")
        adb = MockAdbService(xml_content)
        vision = VisionService(adb)
        self.assertEqual(vision.determine_app_state(), "ACTIVE (Find Page)")

    def test_my_profile_detection(self):
        xml_content = self.load_xml("my_profile.xml")
        adb = MockAdbService(xml_content)
        vision = VisionService(adb)
        self.assertEqual(vision.determine_app_state(), "ACTIVE (My Profile)")

    def test_search_filters_detection(self):
        xml_content = self.load_xml("search_filters.xml")
        adb = MockAdbService(xml_content)
        vision = VisionService(adb)
        self.assertEqual(vision.determine_app_state(), "ACTIVE (Search Filters)")

    def test_like_page_detection(self):
        xml_content = self.load_xml("like_page.xml")
        adb = MockAdbService(xml_content)
        vision = VisionService(adb)
        self.assertEqual(vision.determine_app_state(), "ACTIVE (Like/Visitor Page)")

    def test_today_page_detection(self):
        xml_content = self.load_xml("today_page.xml")
        adb = MockAdbService(xml_content)
        vision = VisionService(adb)
        self.assertEqual(vision.determine_app_state(), "ACTIVE (Today Page)")

    def test_detailed_profile_detection(self):
        xml_content = self.load_xml("detailed_profile.xml")
        adb = MockAdbService(xml_content)
        vision = VisionService(adb)
        self.assertEqual(vision.determine_app_state(), "ACTIVE (Detailed Profile)")

    def test_chat_with_person_detection(self):
        xml_content = self.load_xml("chat_with_person.xml")
        adb = MockAdbService(xml_content)
        vision = VisionService(adb)
        self.assertEqual(vision.determine_app_state(), "ACTIVE (Chat With Person)")

if __name__ == "__main__":
    unittest.main()