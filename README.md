# Meeff Auto-Swiper Bot

An ADB-based bot that automates profile swiping on the Meeff dating app. It uses UI hierarchy dumps to read screen state, optional AI photo scoring via Claude to decide like/skip, and human-like tap/scroll simulation to avoid detection.

---

## How It Works

1. **State machine** — reads the current screen via `adb shell uiautomator dump` and classifies it (Swipe Mode, Detailed Profile, Ad, Chat, etc.)
2. **AI scoring** — takes a screenshot of the profile photo and sends it to Claude for a 0–100 attractiveness score; skips profiles below the configured threshold
3. **Human simulation** — randomised tap coordinates, hesitation delays, and scroll speeds driven by `config.json`

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10+ | |
| ADB | any | must be in `$PATH` |
| Android emulator **or** physical device | Android 9+ | emulator recommended (no FLAG_SECURE) |
| Anthropic API key | — | only needed if AI scoring is enabled |

---

## Setup

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd meeff
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set your Anthropic API key

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Add this to your `~/.bashrc` or `~/.zshrc` to persist it.

---

## Recommended: Android Emulator (no screenshot restrictions)

Physical devices running Meeff enforce `FLAG_SECURE`, which blocks `adb screencap`. Running on an emulator avoids this entirely.

### Install the Android SDK (command-line tools only)

```bash
mkdir -p ~/android-sdk/cmdline-tools
cd ~/android-sdk/cmdline-tools
curl -o cmdline-tools.zip https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
unzip cmdline-tools.zip && mv cmdline-tools latest
```

Add to `~/.bashrc`:

```bash
export ANDROID_HOME=~/android-sdk
export PATH=$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/emulator:$ANDROID_HOME/platform-tools:$PATH
```

### Install emulator and system image

```bash
source ~/.bashrc
yes | sdkmanager --licenses
sdkmanager "emulator" "platform-tools" "system-images;android-34;google_apis_playstore;x86_64" "platforms;android-34"
```

### Create and start the AVD

```bash
echo "no" | avdmanager create avd \
  --name "meeff_bot" \
  --package "system-images;android-34;google_apis_playstore;x86_64" \
  --device "pixel_6"

emulator -avd meeff_bot -gpu host -memory 4096 &
```

Wait ~60 seconds for it to boot, then sign in to Google Play and install Meeff.

### Configure the bot to target the emulator

In `config.json`, set:

```json
"device_serial": "emulator-5554"
```

---

## Physical Device Setup

> **Note:** AI photo scoring will be disabled on physical devices running Meeff due to `FLAG_SECURE`. The bot will still run and like all profiles.

1. Enable **Developer Options** on the device
2. Enable **USB Debugging**
3. Connect via USB and run `adb devices` to confirm it is listed
4. Set `device_serial` in `config.json` to your device serial (e.g. `"t4m76xr8qwvkj7ir"`)

---

## Configuration (`config.json`)

```jsonc
{
    "device_serial": "emulator-5554",  // adb device serial; null = auto-detect

    "timing": {
        "human_tap_hesitation_min": 0.5,   // seconds before each tap
        "human_tap_hesitation_max": 2.0,
        "scroll_duration_min_ms": 300,      // swipe duration
        "scroll_duration_max_ms": 900,
        "read_delay_after_scroll_min": 2.0, // pause after scrolling
        "read_delay_after_scroll_max": 5.0,
        "thinking_before_like_min": 2.0,    // pause before tapping Like
        "thinking_before_like_max": 5.0,
        "delay_after_like_min": 3.0,        // wait after liking
        "delay_after_like_max": 6.0,
        "delay_after_opening_profile": 2.0  // wait after opening detail view
    },

    "behavior": {
        "scrolls_weights": [5, 25, 40, 30]  // probability weights for 0/1/2/3 scrolls
    },

    "ai": {
        "enabled": true,
        "model": "claude-haiku-4-5-20251001",
        "photo_score_threshold": 60,         // skip profiles scoring below this
        "chat_reply_enabled": false
    },

    "coordinates": {
        // Pixel bounds for UI elements — recalibrate if the layout changes
        "main_profile_photo":   {"x_min":  53, "x_max": 1027, "y_min":  434, "y_max": 2105},
        "detailed_nope_button": {"x_min": 334, "x_max":  523, "y_min": 2058, "y_max": 2247},
        "detailed_like_button": {"x_min": 555, "x_max":  744, "y_min": 2058, "y_max": 2247},
        "ad_close_button":      {"x_min": 956, "x_max": 1035, "y_min":  146, "y_max":  225}
    }
}
```

---

## Running

```bash
# Activate venv first
source venv/bin/activate

# Main bot loop
python main.py

# Debug: print current screen state without taking any actions
python debug_state.py
```

---

## Project Structure

```
meeff/
├── main.py                  # Entry point
├── debug_state.py           # Prints current app state (no actions taken)
├── config.json              # All tuneable settings
├── requirements.txt
├── src/
│   ├── adb_service.py       # ADB communication, screenshots, taps, scrolls
│   ├── vision_service.py    # UI hierarchy parsing and state detection
│   ├── ai_service.py        # Claude API integration for photo scoring
│   └── bot_controller.py    # Main state machine loop
├── tests/
│   ├── test_lock_state.py
│   └── test_vision_service.py
└── page_data/               # Sample XML dumps for offline testing
```

---

## Recalibrating Coordinates

If the UI layout changes (app update, different device resolution), run:

```python
from src.adb_service import AdbService
from src.vision_service import VisionService

adb = AdbService()
vision = VisionService(adb)
vision.refresh_screen_data()

for node in ['photo_imageview', 'nope_imageview', 'like_imageview', 'force_open_imageview']:
    print(node, vision.get_node_bounds(node))
```

Update the `coordinates` section of `config.json` with the printed values.
