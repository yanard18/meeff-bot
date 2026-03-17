import subprocess
import time
import sys
import os

class AdbService:
    """The 'Hands' of the bot. Handles all raw communication with the Android device."""
    def __init__(self, package_name="com.noyesrun.meeff.kr"):
        self.package_name = package_name

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

    def tap(self, x, y):
        self.run_command(f"shell input tap {x} {y}")

    def human_tap(self, bounds, margin=20, name="button"):
        """Generalized method to tap any button with human-like evasion."""
        import random
        x = random.randint(bounds["x_min"] + margin, bounds["x_max"] - margin)
        y = random.randint(bounds["y_min"] + margin, bounds["y_max"] - margin)
        
        hesitation = random.uniform(0.5, 1.5)
        print(f"[AdbService] Human-like pause for {hesitation:.2f}s...")
        time.sleep(hesitation)
        
        print(f"[AdbService] Tapping '{name}' at randomized coordinates: ({x}, {y})")
        result = self.run_command(f"shell input tap {x} {y}")
        return result is not None

    def human_scroll_down(self):
        """Simulates a natural human scroll down the page."""
        import random
        # Screen resolution is ~1080x2400. 
        # Start scroll somewhere in the bottom half, swipe up to the top half
        start_x = random.randint(400, 700)
        start_y = random.randint(1600, 2000)
        end_x = start_x + random.randint(-50, 50) # Slight curve in the swipe
        end_y = random.randint(600, 1000)
        
        # Duration between 300ms (fast flick) and 800ms (slow read)
        duration = random.randint(300, 800)
        
        print(f"[AdbService] Scrolling down profile... ({duration}ms)")
        self.run_command(f"shell input swipe {start_x} {start_y} {end_x} {end_y} {duration}")
        
        # Pause to "read" the newly revealed content
        read_time = random.uniform(1.0, 2.5)
        time.sleep(read_time)
