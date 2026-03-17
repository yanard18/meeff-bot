#!/usr/bin/env python3
import subprocess
import time
import random
import sys

def run_adb_command(command):
    try:
        result = subprocess.run(['adb'] + command.split(), capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"ADB command failed: {e}")
        return None

def launch_meeff():
    print("Launching Meeff app...")
    run_adb_command("shell monkey -p com.noyesrun.meeff.kr -c android.intent.category.LAUNCHER 1")
    
    # Wait for the app to load
    print("Waiting 8 seconds for the app to fully load...")
    time.sleep(8)
    print("App should be open now.")

def tap_like_button():
    # Bounds for like_imageview: [554, 1772, 734, 1952]
    # We add a margin of 20 pixels to ensure we don't click the very edge of the button
    min_x = 554 + 20
    max_x = 734 - 20
    min_y = 1772 + 20
    max_y = 1952 - 20
    
    # Generate random coordinates within the safe zone of the button
    tap_x = random.randint(min_x, max_x)
    tap_y = random.randint(min_y, max_y)
    
    print(f"Tapping 'Like' button at randomized coordinates: ({tap_x}, {tap_y})")
    command = f"shell input tap {tap_x} {tap_y}"
    run_adb_command(command)
    print("Tap executed.")

if __name__ == '__main__':
    print("--- Testing Meeff Bot Like Button Tap ---")
    
    # We assume the app is already open for this test
    # If not, you can uncomment launch_meeff()
    # launch_meeff()
    
    # Perform a single tap on the Like button to test functionality
    tap_like_button()
    print("Test finished successfully.")