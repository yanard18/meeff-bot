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
