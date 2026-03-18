import os
import shutil
import time
import sys
import random
from .adb_service import AdbService
from .vision_service import VisionService
from .ai_service import AIService
from clip_critic import ClipCritic

class BotController:
    """The central brain/loop that manages the bot's flow and services."""

    def __init__(self):
        self.adb = AdbService()
        self.vision = VisionService(self.adb)
        ai_conf = self.adb.config.get("ai", {})
        self.ai = AIService(ai_conf)
        clip_threshold = ai_conf.get("clip_threshold", 0.6)
        self.critic = ClipCritic(threshold=clip_threshold)
        print(f"[Bot] Using CLIP critic (threshold={clip_threshold})")

    def _save_training_sample(self, screenshot_path, liked):
        """Copies the screenshot into labeled_data/liked or labeled_data/disliked."""
        if not screenshot_path or not os.path.exists(screenshot_path):
            return
        label = "liked" if liked else "disliked"
        dest_dir = os.path.join("labeled_data", label)
        os.makedirs(dest_dir, exist_ok=True)
        ext = os.path.splitext(screenshot_path)[1] or ".jpg"
        dest = os.path.join(dest_dir, f"{int(time.time())}{ext}")
        shutil.copy(screenshot_path, dest)
        print(f"[Data] Saved training sample → {dest}")

    def _evaluate_profile(self, screenshot_path):
        """Returns True (like) or False (skip). Skips AI if disabled in config."""
        ai_conf = self.adb.config.get("ai", {})
        if not ai_conf.get("enabled", False):
            print("[AI] Scoring disabled in config. Defaulting to like.")
            return True
        return self.critic.evaluate(screenshot_path).liked

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

        launch_attempts = 0
        unknown_streak = 0

        try:
            while True:
                state = self.vision.determine_app_state()
                print(f"[State] {state}")

                if state == "NOT OPENED":
                    launch_attempts += 1
                    if launch_attempts > 3:
                        print(f"[!] App failed to launch after {launch_attempts} attempts. Waiting 30s...")
                        time.sleep(30)
                        launch_attempts = 0
                    else:
                        print(f"[*] App is not open. Launching (attempt {launch_attempts}/3)...")
                        self.adb.launch_app(wait_time=10)
                    continue
                    
                else:
                    launch_attempts = 0

                if state == "ACTIVE (Swipe Mode)":
                    unknown_streak = 0
                    print("[*] Profile deck detected. Tapping photo to open detailed view...")
                    self.adb.human_tap(main_profile_photo, name="Profile Photo")
                    
                    # Short delay to let the detailed profile slide up based on config
                    time.sleep(t_conf["delay_after_opening_profile"])
                    
                elif state == "ACTIVE (Detailed Profile)":
                    unknown_streak = 0
                    print("[*] Reading detailed profile...")

                    # 1. Capture profile photo and score it
                    photo_bounds = self.vision.get_node_bounds("photo_imageview")
                    screenshot_path = self.adb.take_screenshot(crop_bounds=photo_bounds)
                    time.sleep(1)  # brief pause after capture before sending to AI
                    should_like = self._evaluate_profile(screenshot_path)

                    # Save screenshot to labeled_data/ for future CLIP training
                    self._save_training_sample(screenshot_path, should_like)

                    if not should_like:
                        print("[*] AI scored profile below threshold. Tapping Nope...")
                        self.adb.human_tap(c_conf["detailed_nope_button"], name="Nope")
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
                    unknown_streak = 0
                    self._handle_active_chat()

                elif state == "ACTIVE (Ad)":
                    unknown_streak = 0
                    print("[*] WebView ad detected! Closing via close button...")
                    self.adb.human_tap(c_conf["ad_close_button"], margin=10, name="Ad Close Button")
                    time.sleep(2)

                elif state == "ACTIVE (Native Ad)":
                    unknown_streak = 0
                    print("[*] Native ad detected! Pressing back to dismiss...")
                    self.adb.press_back()
                    time.sleep(2)

                elif state == "ACTIVE (Quit Dialog)":
                    unknown_streak = 0
                    print("[*] Quit dialog detected! Tapping Cancel...")
                    cancel_bounds = self.vision.get_node_bounds("negativeButton")
                    if cancel_bounds:
                        self.adb.human_tap(cancel_bounds, name="Cancel (Quit Dialog)")
                    else:
                        self.adb.press_back()
                    time.sleep(1)

                else:
                    unknown_streak += 1
                    print(f"[*] Unknown screen detected (streak: {unknown_streak}/3). Waiting...")
                    if unknown_streak >= 3:
                        print("[*] Stuck for 3 consecutive unknown states — triggering safe escape.")
                        self.adb.safe_escape()
                        unknown_streak = 0
                    else:
                        time.sleep(3)
                
        except KeyboardInterrupt:
            print("\n[*] Stopping Bot...")
