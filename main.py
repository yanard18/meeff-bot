#!/usr/bin/env python3
import os
import subprocess
import time

from dotenv import load_dotenv
load_dotenv()


EMULATOR_BIN = os.path.expanduser("~/android-sdk/emulator/emulator")
ADB_BIN      = os.path.expanduser("~/android-sdk/platform-tools/adb")
AVD_NAME     = "meeff_bot"


def is_emulator_running():
    """Returns True if an Android emulator is already listed by adb."""
    try:
        result = subprocess.run(
            [ADB_BIN, "devices"],
            capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.strip().splitlines()[1:]  # skip header
        return any("emulator" in line and "device" in line for line in lines)
    except Exception:
        return False


def start_emulator():
    """Launches the emulator in the background and waits until adb sees it."""
    print(f"[Emulator] Starting AVD '{AVD_NAME}'...")
    subprocess.Popen(
        [EMULATOR_BIN, "-avd", AVD_NAME, "-gpu", "host",
         "-memory", "4096", "-no-metrics"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True   # detach so it survives if this shell closes
    )

    print("[Emulator] Waiting for device to come online", end="", flush=True)
    for _ in range(60):          # up to 2 minutes
        time.sleep(2)
        print(".", end="", flush=True)
        if is_emulator_running():
            print(" ready!")
            # Extra wait for boot to finish (home screen)
            subprocess.run(
                [ADB_BIN, "wait-for-device", "shell",
                 "while [[ -z $(getprop sys.boot_completed) ]]; do sleep 2; done"],
                timeout=120, capture_output=True
            )
            print("[Emulator] Boot completed.")
            return

    print("\n[Emulator] Timed out waiting for emulator. Proceeding anyway...")


if __name__ == '__main__':
    if not is_emulator_running():
        start_emulator()
    else:
        print("[Emulator] Already running.")

    from src.bot_controller import BotController
    bot = BotController()
    bot.run()
