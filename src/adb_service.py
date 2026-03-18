import subprocess
import time
import sys
import os
import json
import random

class AdbService:
    """The 'Hands' of the bot. Handles all raw communication with the Android device."""
    def __init__(self, package_name="com.noyesrun.meeff.kr"):
        self.package_name = package_name
        self.config = self._load_config()

    def _load_config(self):
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Error loading config.json: {e}. Using defaults.")
            return {"timing": {"human_tap_hesitation_min": 0.5, "human_tap_hesitation_max": 1.5, "scroll_duration_min_ms": 300, "scroll_duration_max_ms": 800, "read_delay_after_scroll_min": 1.0, "read_delay_after_scroll_max": 2.5}}

    def run_command(self, command, check=True):
        """Runs a generic ADB command."""
        try:
            result = subprocess.run(['adb'] + command.split(), capture_output=True, text=True, check=check)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            # print(f"[AdbService] Error running command: {command}")
            return None
        except FileNotFoundError:
            print("[!] Critical Error: ADB is not installed or not in your system PATH.")
            sys.exit(1)

    def is_device_connected(self):
        return self.run_command('get-state', check=False) == 'device'

    def is_device_awake(self):
        power_output = self.run_command('shell dumpsys power', check=False)
        return power_output and "mWakefulness=Asleep" not in power_output

    def is_screen_locked(self):
        """Checks if the device is currently at the lockscreen/keyguard."""
        # On modern Android (especially Xiaomi/Redmi), checking mDreamingLockscreen or mShowingLockscreen
        # in the window dump is the most reliable way.
        window_output = self.run_command('shell dumpsys window', check=False)
        if not window_output:
            return False
        
        # Look for common lockscreen indicators
        if "mDreamingLockscreen=true" in window_output or "mShowingLockscreen=true" in window_output:
            return True
            
        # Fallback for some versions: check if the keyguard is showing
        keyguard_output = self.run_command('shell dumpsys keyguard', check=False)
        if keyguard_output and "mShowing=true" in keyguard_output:
            return True
            
        return False

    def launch_app(self, wait_time=8):
        print(f"[AdbService] Launching {self.package_name}...")
        self.run_command(f"shell monkey -p {self.package_name} -c android.intent.category.LAUNCHER 1")
        time.sleep(wait_time)

    def get_window_dump(self):
        """Dumps the current UI hierarchy to an XML string."""
        # Dump to device SD card
        dump_path = "/sdcard/window_dump.xml"
        self.run_command(f"shell uiautomator dump {dump_path}", check=False)
        
        # Pull the content directly to stdout to avoid writing files to PC disk if possible
        # Some older ADB versions require pulling to a file first. We'll pull to a temp file.
        local_path = "temp_dump.xml"
        self.run_command(f"pull {dump_path} {local_path}", check=False)
        
        if os.path.exists(local_path):
            with open(local_path, 'r', encoding='utf-8') as f:
                content = f.read()
            os.remove(local_path)
            return content
        return None

    def press_back(self):
        """Presses the Android back button."""
        self.run_command("shell input keyevent 4")

    def human_tap(self, bounds, margin=20, name="button"):
        """Generalized method to tap any button with human-like evasion."""
        x = random.randint(bounds["x_min"] + margin, bounds["x_max"] - margin)
        y = random.randint(bounds["y_min"] + margin, bounds["y_max"] - margin)
        
        t_min = self.config["timing"]["human_tap_hesitation_min"]
        t_max = self.config["timing"]["human_tap_hesitation_max"]
        hesitation = random.uniform(t_min, t_max)
        print(f"[AdbService] Human-like pause for {hesitation:.2f}s...")
        time.sleep(hesitation)
        
        print(f"[AdbService] Tapping '{name}' at randomized coordinates: ({x}, {y})")
        result = self.run_command(f"shell input tap {x} {y}")
        return result is not None

    def take_screenshot(self, crop_bounds=None):
        """Captures the current screen via ADB and saves it as a PNG.

        Uses the pull method (screencap on device → adb pull) which is
        more reliable than exec-out for binary data (avoids CRLF corruption).

        Args:
            crop_bounds: Optional dict {x_min, y_min, x_max, y_max} to crop
                         the image to a region (e.g. just the profile photo).

        Returns:
            str: Local file path to the saved PNG, or None on failure.
        """
        os.makedirs('screenshots', exist_ok=True)
        device_path = "/sdcard/_meeff_shot.png"
        raw_path = "screenshots/_raw.png"

        try:
            print("[AdbService] Taking screenshot...")

            # Step 1: capture on device
            self.run_command(f"shell screencap -p {device_path}", check=False)

            # Step 2: pull to local disk
            self.run_command(f"pull {device_path} {raw_path}", check=False)

            if not os.path.exists(raw_path) or os.path.getsize(raw_path) == 0:
                print("[AdbService] Screenshot failed: file missing or empty after pull.")
                return None

            raw_size_kb = os.path.getsize(raw_path) / 1024
            print(f"[AdbService] Raw screenshot pulled: {raw_path} ({raw_size_kb:.1f} KB)")

            # Step 3: open and optionally crop
            from PIL import Image
            img = Image.open(raw_path)
            print(f"[AdbService] Image opened: {img.width}x{img.height}px, mode={img.mode}")

            if crop_bounds:
                img = img.crop((
                    crop_bounds['x_min'], crop_bounds['y_min'],
                    crop_bounds['x_max'], crop_bounds['y_max']
                ))
                print(f"[AdbService] Cropped to {img.width}x{img.height}px "
                      f"(x:{crop_bounds['x_min']}-{crop_bounds['x_max']}, "
                      f"y:{crop_bounds['y_min']}-{crop_bounds['y_max']})")
            else:
                print("[AdbService] No crop bounds — using full screenshot.")

            # Step 4: detect all-black image (FLAG_SECURE blocks ADB screenshots)
            from PIL import ImageStat
            stat = ImageStat.Stat(img.convert("RGB"))
            if all(m < 2 for m in stat.mean):
                print("[AdbService] Screenshot is all black — app has FLAG_SECURE. Cannot score photo.")
                os.remove(raw_path)
                return None

            # Step 5: save final file
            path = f"screenshots/profile_{int(time.time())}.png"
            img.save(path)
            final_size_kb = os.path.getsize(path) / 1024
            print(f"[AdbService] Screenshot saved: {path} ({final_size_kb:.1f} KB)")

            os.remove(raw_path)
            return path

        except Exception as e:
            print(f"[AdbService] Screenshot error: {e}")
            return None

    def type_text(self, text):
        """Types a string into the currently focused input field.

        Args:
            text: The string to type. Special characters will be escaped.

        Returns:
            bool: True on success, False on failure.

        Implementation note (Phase 6):
            adb shell input text "{escaped_text}"
            Spaces must be escaped as %s for ADB input.
        """
        raise NotImplementedError("Phase 6: type_text() not yet implemented.")

    def human_scroll_down(self):
        """Simulates a natural human scroll down the page."""
        # Screen resolution is ~1080x2400.
        # Start scroll somewhere in the bottom half, swipe up to the top half
        start_x = random.randint(400, 700)
        start_y = random.randint(1600, 2000)
        end_x = start_x + random.randint(-50, 50) # Slight curve in the swipe
        end_y = random.randint(600, 1000)
        
        # Duration based on config
        d_min = self.config["timing"]["scroll_duration_min_ms"]
        d_max = self.config["timing"]["scroll_duration_max_ms"]
        duration = random.randint(d_min, d_max)
        
        print(f"[AdbService] Scrolling down profile... ({duration}ms)")
        self.run_command(f"shell input swipe {start_x} {start_y} {end_x} {end_y} {duration}")
        
        # Pause to "read" the newly revealed content based on config
        r_min = self.config["timing"]["read_delay_after_scroll_min"]
        r_max = self.config["timing"]["read_delay_after_scroll_max"]
        read_time = random.uniform(r_min, r_max)
        print(f"[AdbService] Reading new content for {read_time:.2f}s...")
        time.sleep(read_time)
