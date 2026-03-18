import os
import time
import sys
import random
from .adb_service import AdbService
from .vision_service import VisionService
from .ai_service import AIService

class BotController:
    """The central brain/loop that manages the bot's flow and services."""

    def __init__(self):
        self.adb = AdbService()
        self.vision = VisionService(self.adb)
        self.ai = AIService(self.adb.config.get("ai", {}))

    def _evaluate_profile(self, screenshot_path):
        """Scores the profile photo via AI and returns True (like) or False (skip).

        Falls back to True if AI is disabled, screenshot failed, or API errors.
        Always cleans up the screenshot file after scoring.
        """
        ai_conf = self.adb.config.get("ai", {})
        if not ai_conf.get("enabled", False) or not screenshot_path:
            return True

        try:
            score = self.ai.score_profile_photo(screenshot_path)
            threshold = ai_conf.get("photo_score_threshold", 60)
            print(f"[AI] Photo score: {score:.0f}/100  (threshold: {threshold})")
            return score >= threshold
        except Exception as e:
            print(f"[!] AI scoring failed: {e}. Defaulting to like.")
            return True
        finally:
            if screenshot_path and os.path.exists(screenshot_path):
                os.remove(screenshot_path)

    def _handle_active_chat(self):
        """Hook: handles an open individual chat screen.

        Current behavior (Phase 0–5): presses back to exit the chat.
        Phase 6: will call self.vision.get_chat_messages(), then
                 self.ai.generate_chat_reply(), then self.adb.type_text()
                 to compose and send a human-like reply.
        """
        print("[*] Individual chat detected. Exiting chat (AI reply not yet enabled).")
        self.adb.press_back()
        time.sleep(2)

    def verify_system(self):
        print("[*] Checking system and device...")
        if not self.adb.is_device_connected():
            print("[!] No device connected. Exiting.")
            sys.exit(1)
            
        if not self.adb.is_device_awake():
            print("[!] Device is asleep. Please wake it up. Exiting.")
            sys.exit(1)

        # New logic: Check for lockscreen
        while self.adb.is_screen_locked():
            print("[!] Device is LOCKED. Please unlock the screen to proceed...")
            time.sleep(5)
            
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
        config = self.adb.config
        t_conf = config["timing"]
        b_conf = config["behavior"]
        c_conf = config["coordinates"]
        main_profile_photo = c_conf["main_profile_photo"]
        detailed_like_button = c_conf["detailed_like_button"]
        
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
                    print("[*] Profile deck detected. Tapping photo to open detailed view...")
                    self.adb.human_tap(main_profile_photo, name="Profile Photo")
                    
                    # Short delay to let the detailed profile slide up based on config
                    time.sleep(t_conf["delay_after_opening_profile"])
                    
                elif state == "ACTIVE (Detailed Profile)":
                    print("[*] Reading detailed profile...")

                    # 1. Capture profile photo and ask AI to score it
                    photo_bounds = self.vision.get_node_bounds("force_open_imageview")
                    screenshot_path = self.adb.take_screenshot(crop_bounds=photo_bounds)
                    should_like = self._evaluate_profile(screenshot_path)

                    if not should_like:
                        print("[*] AI scored profile below threshold. Skipping...")
                        self.adb.press_back()
                        time.sleep(1)
                        continue

                    # 2. Decide how many times to scroll based on config weights
                    scroll_weights = b_conf["scrolls_weights"]
                    scrolls = random.choices([0, 1, 2, 3], weights=scroll_weights)[0]

                    if scrolls > 0:
                        for i in range(scrolls):
                            print(f"[*] Executing scroll {i+1} of {scrolls}...")
                            self.adb.human_scroll_down()

                    # 3. Final hesitation before making a decision based on config
                    read_time = random.uniform(t_conf["thinking_before_like_min"], t_conf["thinking_before_like_max"])
                    print(f"[*] Thinking for {read_time:.2f}s...")
                    time.sleep(read_time)

                    # 4. Tap the Like button
                    success = self.adb.human_tap(detailed_like_button, name="Detailed Like")
                    if success:
                        print("[+] Successfully liked profile.")
                    else:
                        print("[!] Failed to tap Like.")

                    # Wait for the next profile to load after liking based on config
                    post_swipe_delay = random.uniform(t_conf["delay_after_like_min"], t_conf["delay_after_like_max"])
                    print(f"[*] Waiting {post_swipe_delay:.2f}s before next action...\n")
                    time.sleep(post_swipe_delay)

                elif state == "ACTIVE (Chat With Person)":
                    self._handle_active_chat()

                elif state == "ACTIVE (Ad)":
                    print("[*] WebView ad detected! Closing via close button...")
                    self.adb.human_tap(c_conf["ad_close_button"], margin=10, name="Ad Close Button")
                    time.sleep(2)

                elif state == "ACTIVE (Native Ad)":
                    print("[*] Native ad detected! Pressing back to dismiss...")
                    self.adb.press_back()
                    time.sleep(2)

                elif state == "ACTIVE (Quit Dialog)":
                    print("[*] Quit dialog detected! Tapping Cancel...")
                    cancel_bounds = self.vision.get_node_bounds("negativeButton")
                    if cancel_bounds:
                        self.adb.human_tap(cancel_bounds, name="Cancel (Quit Dialog)")
                    else:
                        self.adb.press_back()
                    time.sleep(1)

                else:
                    # Unknown state (like an ad or chat screen). Just wait and check again.
                    print("[*] Unknown screen or Ad detected. Waiting...")
                    time.sleep(3)
                
        except KeyboardInterrupt:
            print("\n[*] Stopping Bot...")
