import time
import sys
from .adb_service import AdbService
from .vision_service import VisionService

class BotController:
    """The central brain/loop that manages the bot's flow and services."""
    
    def __init__(self):
        self.adb = AdbService()
        self.vision = VisionService(self.adb)

    def verify_system(self):
        print("[*] Checking system and device...")
        if not self.adb.is_device_connected():
            print("[!] No device connected. Exiting.")
            sys.exit(1)
            
        if not self.adb.is_device_awake():
            print("[!] Device is asleep. Please wake it up. Exiting.")
            sys.exit(1)
            
        print("[+] System checks passed.")

    def run_state_printer(self):
        """A simple loop to constantly print the current app state."""
        self.verify_system()
        
        print("\n" + "="*40)
        print("    Meeff State Tracker Started")
        print("    Press Ctrl+C to stop")
        print("="*40 + "\n")

        try:
            while True:
                state = self.vision.determine_app_state()
                print(f"[State] {state}")
                
                # Wait 2 seconds before checking again to avoid overloading the phone
                time.sleep(2)
                
        except KeyboardInterrupt:
            print("\n[*] Stopping State Tracker...")

    def run(self):
        """The main intelligent loop that acts based on the current app state."""
        self.verify_system()
        
        # Like button coordinates extracted from previous UI dump
        like_button_bounds = {"x_min": 554, "x_max": 734, "y_min": 1772, "y_max": 1952}
        
        print("\n" + "="*40)
        print("    Meeff Smart Auto-Swiper Started")
        print("    Press Ctrl+C to stop")
        print("="*40 + "\n")

        try:
            while True:
                state = self.vision.determine_app_state()
                print(f"[State] {state}")
                
                if state == "NOT OPENED":
                    print("[*] App is not open. Launching...")
                    self.adb.launch_app(wait_time=10)
                elif state == "ACTIVE (Swipe Mode)":
                    print("[*] Profile detected. Executing 'Like'...")
                    success = self.adb.human_tap(like_button_bounds, name="Like")
                    if success:
                        print("[+] Successfully liked profile.")
                    else:
                        print("[!] Failed to tap Like.")
                    
                    # Wait a bit after swiping before the next check to simulate human pacing
                    import random
                    post_swipe_delay = random.uniform(1.5, 3.5)
                    print(f"[*] Waiting {post_swipe_delay:.2f}s before next action...\n")
                    time.sleep(post_swipe_delay)
                else:
                    # Unknown state (like an ad or chat screen). Just wait and check again.
                    print("[*] Unknown screen or Ad detected. Waiting...")
                    time.sleep(3)
                
        except KeyboardInterrupt:
            print("\n[*] Stopping Bot...")
