import unittest
import os
import sys

# Ensure we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.adb_service import AdbService

class MockAdbCommand:
    """A fake wrapper to simulate ADB responses for shell commands."""
    def __init__(self, responses):
        self.responses = responses

    def run_command(self, command, check=True):
        # We find which command is being called and return its mocked response
        for cmd_key in self.responses:
            if cmd_key in command:
                return self.responses[cmd_key]
        return ""

class TestLockState(unittest.TestCase):
    def test_detect_locked_screen(self):
        # Create a mock response for window dump where lockscreen is true
        mock_dump = "mDreamingLockscreen=true mShowingLockscreen=true"
        adb = AdbService()
        # Override the run_command method for testing
        adb.run_command = MockAdbCommand({"shell dumpsys window": mock_dump}).run_command
        
        self.assertTrue(adb.is_screen_locked(), "Should detect that the screen is locked")

    def test_detect_unlocked_screen(self):
        # Create a mock response for window dump where lockscreen is false
        mock_dump = "mDreamingLockscreen=false mShowingLockscreen=false"
        adb = AdbService()
        adb.run_command = MockAdbCommand({"shell dumpsys window": mock_dump}).run_command
        
        self.assertFalse(adb.is_screen_locked(), "Should detect that the screen is UNLOCKED")

if __name__ == "__main__":
    unittest.main()
