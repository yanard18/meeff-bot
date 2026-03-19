"""Android emulator lifecycle management.

Separated from main.py so bot assembly (build_bot) doesn't depend on
emulator infrastructure. Physical-device runs simply skip calling these.
"""
import os
import subprocess
import time

EMULATOR_BIN = os.path.expanduser("~/android-sdk/emulator/emulator")
ADB_BIN      = os.path.expanduser("~/android-sdk/platform-tools/adb")
AVD_NAME     = "meeff_bot"


def is_running() -> bool:
    """Return True if an Android emulator is already listed by adb."""
    try:
        result = subprocess.run(
            [ADB_BIN, "devices"],
            capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.strip().splitlines()[1:]
        return any("emulator" in line and "device" in line for line in lines)
    except Exception:
        return False


def start() -> None:
    """Launch the emulator in the background and wait until adb sees it."""
    print(f"[Emulator] Starting AVD '{AVD_NAME}'...")
    subprocess.Popen(
        [EMULATOR_BIN, "-avd", AVD_NAME, "-gpu", "host",
         "-memory", "4096", "-no-metrics"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    print("[Emulator] Waiting for device to come online", end="", flush=True)
    for _ in range(60):
        time.sleep(2)
        print(".", end="", flush=True)
        if is_running():
            print(" ready!")
            subprocess.run(
                [ADB_BIN, "wait-for-device", "shell",
                 "while [[ -z $(getprop sys.boot_completed) ]]; do sleep 2; done"],
                timeout=120, capture_output=True
            )
            print("[Emulator] Boot completed.")
            return

    print("\n[Emulator] Timed out waiting for emulator. Proceeding anyway...")
