#!/usr/bin/env python3
import subprocess
import time
import random
import sys

class MeeffBot:
    def __init__(self):
        self.package_name = "com.noyesrun.meeff.kr"
        self.like_button_bounds = {"x_min": 554, "x_max": 734, "y_min": 1772, "y_max": 1952}

    def _run_adb_command(self, command, check=True):
        try:
            result = subprocess.run(['adb'] + command.split(), capture_output=True, text=True, check=check)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"[!] ADB command failed: {e}")
            return None
        except FileNotFoundError:
            print("[!] Critical Error: ADB is not installed or not in your system PATH.")
            sys.exit(1)

    def verify_device_ready(self):
        print("[*] Performing pre-flight device checks...")
        
        # Simpler check using 'get-state' instead of parsing 'devices'
        if self._run_adb_command('get-state', check=False) != 'device':
            print("[!] No devices connected or authorized via ADB.")
            return False

        power_output = self._run_adb_command('shell dumpsys power', check=False)
        if power_output and "mWakefulness=Asleep" in power_output:
            print("[!] Device screen appears to be ASLEEP. Please wake it up.")
            return False

        print("[+] Device is awake and ready.")
        return True

    def launch_app(self, wait_time=10):
        print(f"[*] Launching Meeff ({self.package_name})...")
        self._run_adb_command(f"shell monkey -p {self.package_name} -c android.intent.category.LAUNCHER 1")
        print(f"[*] Waiting {wait_time} seconds for the app to fully load...")
        time.sleep(wait_time)
        print("[+] App should be loaded.")

    def _human_tap(self, bounds, margin=20, name="button"):
        """Generalized method to tap any button with human-like evasion."""
        x = random.randint(bounds["x_min"] + margin, bounds["x_max"] - margin)
        y = random.randint(bounds["y_min"] + margin, bounds["y_max"] - margin)
        
        hesitation = random.uniform(0.5, 1.5)
        print(f"[*] Human-like pause for {hesitation:.2f}s...")
        time.sleep(hesitation)
        
        print(f"[*] Tapping '{name}' at randomized coordinates: ({x}, {y})")
        result = self._run_adb_command(f"shell input tap {x} {y}")
        
        if result is not None:
            print(f"[+] Successfully tapped {name}.")
        else:
            print(f"[!] Failed to tap {name}. Check ADB permissions.")

    def tap_like(self):
        self._human_tap(self.like_button_bounds, name="Like")

    def run(self):
        print("\n" + "="*40)
        print("    Starting Meeff Automation Bot")
        print("="*40 + "\n")
        
        if not self.verify_device_ready():
            print("\n[!] Bot initialization failed. Exiting.")
            sys.exit(1)
            
        print("-" * 20)
        self.launch_app(wait_time=10)
        self.tap_like()
        
        print("\n" + "="*40)
        print("    Bot Execution Completed")
        print("="*40 + "\n")

if __name__ == '__main__':
    bot = MeeffBot()
    bot.run()