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
