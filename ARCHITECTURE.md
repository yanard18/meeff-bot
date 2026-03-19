# Meeff Bot — Architecture Reference

> This file is the single source of truth for understanding the design of this codebase.
> Written for AI context loading: every section is self-contained and precise.

---

## 1. What This Program Is

An Android UI automation bot for the Meeff dating app. It runs on an emulator or physical device
via ADB (Android Debug Bridge). It reads the current UI state by dumping and parsing the XML
hierarchy (`uiautomator dump`), decides what action to take using a priority-sorted task list,
and executes that action via ADB tap/swipe/type commands. It uses a local CLIP model to score
profile photos (like/nope) and the Claude API to generate chat replies.

**Entry point:** `main.py → build_bot() → Orchestrator.run()`
**Config:** `config.json` (loaded once at startup via AdbService)
**Runtime:** single-threaded, blocking; StatusBar renders in a separate daemon thread

---

## 2. Layered Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  main.py  — wires everything together, starts Orchestrator      │
├─────────────────────────────────────────────────────────────────┤
│  Orchestrator  — priority-sorted tick loop (app-agnostic)       │
├──────────────────────────┬──────────────────────────────────────┤
│  Tasks (8 concrete)      │  BotContext (dependency container)   │
│  src/tasks/*.py          │  src/core/context.py                 │
├──────────────────────────┼──────────────────────────────────────┤
│  Platform (abstract)     │  Services                            │
│  src/core/platform.py    │  AdbService   — device I/O           │
│                          │  VisionService — XML parsing utility  │
│  MeeffPlatform           │  AIService    — Claude API wrapper   │
│  src/platforms/meeff.py  │  ClipCritic   — local CLIP scorer    │
│  (state detection,       │  HarvestService — profile DB writes  │
│   navigation, queries)   │  ProfileStore — SQLite persistence   │
│                          │  MessageGenerator — chat reply gen   │
└──────────────────────────┴──────────────────────────────────────┘
```

**Key boundary:** `VisionService` is a pure XML parsing utility — it knows nothing about Meeff.
All Meeff-specific resource-id knowledge (state fingerprints, UI queries) lives in `MeeffPlatform`.
Tasks only call abstract `Platform` methods — zero task code changes when adding a new app.

---

## 3. The Orchestrator Tick Loop

The entire runtime is one `while True` loop. Each iteration ("tick") is:

```
TICK START
│
├─ 1. platform.detect_state()
│      → MeeffPlatform calls vision.refresh_screen_data() (ADB XML dump, ~500ms)
│      → Collects all resource-id suffixes and content-descs from parsed tree
│      → Walks _SCREEN_FINGERPRINTS list in order, returns first match
│      → Returns a state constant string (e.g. "ACTIVE (Swipe Mode)")
│
├─ 2. status.update_mode(state)   [thread-safe, StatusBar daemon re-renders]
│
├─ 3. for task in tasks_by_descending_priority:
│        if task.is_eligible(state):
│            if task.needs_navigation(state):
│                nav_attempts[task] += 1
│                if nav_attempts[task] >= nav_failure_threshold (default 3):
│                    task.cancel_navigation(ctx)     ← reset timers/state
│                    nav_attempts[task] = 0
│                else:
│                    task.navigate_to(ctx)            ← tap a tab, etc.
│            else:
│                nav_attempts.pop(task)
│                task.run(ctx, state)                 ← do the actual work
│            break   ← only ONE task runs per tick
│
└─ 4. time.sleep(loop_interval)   [default 1.0s, but tasks block for much longer]
```

**Critical invariant:** Only the first eligible task (highest priority) runs per tick.
All `time.sleep()` calls inside `task.run()` block the entire loop.
The `loop_interval` sleep is additive after task completion, not a real interval.

---

## 4. Task Registry

All tasks sorted by descending priority. The orchestrator walks this list every tick.

| Priority | Class | Type | Eligible When | What It Does |
|----------|-------|------|---------------|--------------|
| **100** | `DialogTask` | Reactive | state in DIALOG_STATES | Dismiss ads, overlays, match popups. Always first — dialogs block everything. |
| **60** | `MatchedProfileTask` | Reactive | state == MATCHED_FRIEND_PROFILE | Harvest profile data, tap "Send message" → transitions to ChatTask |
| **50** | `ChatTask` | Reactive | state == CHAT_WITH_PERSON | Send/receive one message per tick. Maintains per-session state. Leaves by pressing back. |
| **15** | `ChatQueueTask` | Scheduled | state == CHAT_LIST OR any timer due | Opens chat candidates one by one. Owns chat_queue and likes timers. Priority queue: matched(+2) > unread(+1). |
| **10** | `LikePageTask` | Reactive | state == LIKE_VISITOR_PAGE | Tap first liked profile thumbnail. If none, navigate back to swipe. |
| **5** | `ProfileEvalTask` | Reactive | state == DETAILED_PROFILE | Screenshot → CLIP score → scroll 0-3x → like or nope. Saves training data. |
| **5** | `SwipeTask` | Reactive | state == SWIPE_MODE | Tap profile card to open detailed view. No scoring here — just opens. |
| **1** | `RecoveryTask` | Catch-all | always True | Launch app if closed. safe_escape() after 3 consecutive unknown states. |

**Task types explained:**
- **Reactive**: `needs_navigation()` always returns False. Runs only when the UI is already on the right screen.
- **Scheduled**: `needs_navigation()` returns True when a timer is due but the UI is wrong. Orchestrator calls `navigate_to()` that tick and `run()` next tick (after navigation).

---

## 5. State Machine — All States and Detection

`MeeffPlatform.detect_state()` walks `_SCREEN_FINGERPRINTS` in order (first match wins).
Detection uses two sets: `res_ids` (resource-id suffixes) and `descs` (content-desc values).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ STATE                      │ DETECTION FINGERPRINT                          │
├────────────────────────────┼────────────────────────────────────────────────┤
│ NOT OPENED                 │ No node has package == "com.noyesrun.meeff.kr" │
│ UNKNOWN (Failed to read)   │ uiautomator dump failed or XML parse error     │
├────────────────────────────┼────────────────────────────────────────────────┤
│ ACTIVE (Quit Dialog)       │ messageTextView + negativeButton in res_ids    │
│ ACTIVE (Suggest Meeff)     │ md_root in res_ids                             │
│ ACTIVE (Match Complete)    │ target_photo_imageview in res_ids              │
│ ACTIVE (Ad)                │ "Ad closed" or "Close ad" in content-descs     │
│ ACTIVE (Native Ad)         │ native_ad_conatiner in res_ids [app typo]      │
├────────────────────────────┼────────────────────────────────────────────────┤
│ ACTIVE (Matched Friend     │ open_chat_layout in res_ids                    │
│         Profile)           │ (intermediate screen before chat opens)        │
│ ACTIVE (Detailed Profile)  │ force_open_imageview OR answer_layout          │
│ ACTIVE (Swipe Mode)        │ action_layout OR like_imageview                │
│ ACTIVE (Find Page)         │ voice_bloom_imageview OR vibe_meet_imageview   │
│ ACTIVE (Chat With Person)  │ message_edittext OR send_imageview             │
│ ACTIVE (Chat List)         │ last_msg_textview OR local_time_textview       │
│ ACTIVE (My Profile)        │ plus_layout OR ruby_count_textview             │
│ ACTIVE (Search Filters)    │ distance_seekbar                               │
│ ACTIVE (Like/Visitor Page) │ option_imageview OR no_result_title_textview   │
│ ACTIVE (Today Page)        │ refresh_layout                                 │
│ ACTIVE (Unknown Screen/Ad) │ fallback — none of the above matched           │
└────────────────────────────┴────────────────────────────────────────────────┘
```

State constants are in `src/core/states.py`. All task `is_eligible()` use `==` against these constants (not substring matching).

**DIALOG_STATES** set = {QUIT_DIALOG, SUGGEST_MEEFF, MATCH_COMPLETE, AD, NATIVE_AD}
These are checked first in `_SCREEN_FINGERPRINTS` because dialogs overlay other screens.

---

## 6. Key Workflows

### 6a. Normal Swipe → Evaluate → Like flow

```
SWIPE_MODE
  └─ SwipeTask.run()
       tap "touch_layout" (profile photo, above action_layout safe zone)
       sleep(delay_after_opening_profile)
         │
         ▼
DETAILED_PROFILE
  └─ ProfileEvalTask.run()
       take_screenshot(crop_bounds=photo_imageview)
       harvest_profile() → ProfileStore (name, age, bio, photo)
       ClipCritic.evaluate(screenshot) → liked: bool   [if clip_enabled]
       save_sample() → labeled_data/{liked|disliked}/
       record_decision() → ProfileStore

       if nope:
           tap nope_imageview → back to SWIPE_MODE

       if like:
           human_scroll_down() × [0,1,2,3] (weighted: 5/25/40/30)
           sleep(thinking_before_like: 2–5s)
           tap like_imageview
           sleep(delay_after_like: 3–6s)
           → back to SWIPE_MODE
```

### 6b. Chat Queue flow (timer-driven)

```
SWIPE_MODE (or any screen)
  └─ ChatQueueTask._any_timer_due() == True
     ChatQueueTask.needs_navigation() == True
     Orchestrator calls navigate_to():
         reset due timers
         navigate_to_chat_list() → tap tab_dashboard
         sleep(1.5)
         │
         ▼
CHAT_LIST
  └─ ChatQueueTask.run()  [new session]
       reset_due_timers()
       platform.get_chat_candidates()
         ├─ _get_all_matched_friend_cards() → expire_progressbar nodes → {bounds, name}
         └─ _get_chat_list_rows()           → last_msg_textview nodes → {name, bounds, has_unread}
       _prioritize(): matched(+2) + unread(+1) → sorted queue
       pop first candidate → human_tap(bounds)
       sleep(1.5)
         │
         ▼  [if matched friend card was tapped]
MATCHED_FRIEND_PROFILE
  └─ MatchedProfileTask.run()   [priority 60, runs before ChatTask]
       harvest_profile() → ProfileStore
       tap open_chat_layout ("Send a message" button)
       sleep(1.5)
         │
         ▼  [or directly if unread chat row was tapped]
CHAT_WITH_PERSON
  └─ ChatTask.run()  [priority 50, runs every tick while on this screen]
       harvest_chat_contact() → profile_id  [once per session]
       get_chat_messages() → list[{text, direction}]
       record_new_messages() → ProfileStore

       if waiting_since is set:
           check messages[msg_count_at_send:] for "received" direction
           if got reply: clear waiting_since, return  [respond next tick]
           elif elapsed < timeout(30s): return  [keep waiting]
           else: _leave()  [press back, reset session state]
           return

       generate_reply(messages, profile) → str | None
       if reply:
           tap message_edittext, type_text_human(), tap send_imageview
           set waiting_since = now
       else:
           _leave()

       _leave(): press_back(), reset_session_state(), sleep(back_navigation_delay)
         │
         ▼  [back pressed → state returns to CHAT_LIST]
CHAT_LIST
  └─ ChatQueueTask.run()  [next candidate from queue, or _finish()]
       if queue empty OR session timeout:
           _finish(): clear queue, navigate_to_swipe()
```

### 6c. Likes check flow

```
CHAT_LIST (reached via chat_queue or likes timer)
  └─ ChatQueueTask._finish()  [when queue empty after chat session]
       navigate_to_swipe()   ← NOTE: goes to swipe, NOT likes

  [When likes timer fires separately:]
  ChatQueueTask.is_eligible() True (timer due)
  navigate_to_chat_list()
  run(): no candidates → _finish() → navigate_to_swipe()

  [Reaching LIKE_VISITOR_PAGE requires navigate_to_likes() from platform]
  [Currently: ChatQueueTask navigates to swipe after exhausting candidates]
  [LikePageTask handles the page reactively when the user or another flow lands there]

LIKE_VISITOR_PAGE
  └─ LikePageTask.run()
       platform.get_liked_profiles() → [LikedProfile(bounds)] via thumb_photo_imageview
       if profiles: tap first → opens DETAILED_PROFILE → ProfileEvalTask handles
       if empty: navigate_to_swipe()
```

### 6d. Recovery flow

```
Any unknown state (streak < 3):
  └─ RecoveryTask.run()
       unknown_streak += 1
       sleep(3)

Unknown state streak >= 3:
  └─ RecoveryTask.run()
       safe_escape():
           keyevent 3 (Home)
           am kill-all
           am force-stop com.noyesrun.meeff.kr
           sleep(3)
           launch_app(wait_time=10)
       unknown_streak = 0

NOT OPENED:
  └─ RecoveryTask.run()
       launch_attempts += 1
       if > 3 attempts: sleep(30), reset counter
       else: safe_escape()  [which relaunches the app]
```

---

## 7. Service Contracts

### AdbService (`src/adb_service.py`)
The only class that talks to the Android device. All other code goes through this.

```
Core internal: _invoke_adb(args, check) → str | None
    Builds: [adb_path] + ([-s, device_serial] if set) + args
    Handles: CalledProcessError → None, FileNotFoundError → sys.exit(1)

Public API:
    run_command(cmd_string, check=True) → _invoke_adb(cmd.split())
    _run_adb(args_list)                → _invoke_adb(args, check=False)
    is_device_connected()              → 'get-state' == 'device'
    is_device_awake()                  → dumpsys power
    is_screen_locked()                 → dumpsys window / dumpsys keyguard
    launch_app(wait_time=8)            → shell monkey -p <pkg>
    get_window_dump()                  → uiautomator dump → pull → read → delete
    get_screen_width()                 → shell wm size → int (fallback: 1080)
    press_back()                       → keyevent 4
    safe_escape()                      → Home + kill-all + force-stop + relaunch
    human_tap(bounds, margin=20)       → randomized coords ± margin, hesitation sleep
    human_scroll_down()                → input swipe with random duration + read delay
    type_text_human(text)              → per-char _run_adb, word-boundary pauses
    take_screenshot(crop_bounds=None)  → screencap/emu screenshot → PIL crop → JPEG

Screenshot strategy:
    emulator: adb emu screenrecord screenshot <path>  (avoids -gpu host blank issue)
    physical: shell screencap -p → pull
    FLAG_SECURE detection: if full image mean < 2 on all channels → return None
```

### VisionService (`src/vision_service.py`)
Pure XML utility. No Meeff knowledge. No state detection. Just parses the tree.

```
State:
    cached_tree: ET.Element | None   — result of last refresh_screen_data()
    _screen_width: int | None        — lazy-loaded via adb.get_screen_width()

API:
    refresh_screen_data() → bool          — pulls XML dump, parses it, caches
    get_node_bounds(resource_id_suffix)   — first matching node's {x_min,y_min,x_max,y_max}
    get_node_text(resource_id_suffix)     — first matching node's text attr
    get_all_node_texts(resource_id_suffix)— all matching nodes' text (for repeated Q&A)
    get_node_bounds_by_desc(content_desc) — first node with matching content-desc
    collect_resource_ids() → set[str]     — all resource-id suffixes in tree
    collect_content_descs() → set[str]    — all content-desc values in tree
    build_parent_map() → dict             — child→parent for upward traversal
    get_chat_messages(msg_id_suffixes)    — list[{text, direction}]
        direction heuristic: x_min > screen_width//2 → 'sent', else 'received'

_parse_bounds(node) → dict | None         — parses '[x1,y1][x2,y2]' format
```

### MeeffPlatform (`src/platforms/meeff.py`)
Implements Platform ABC. Owns ALL Meeff-specific knowledge.

```
detect_state() — refresh XML → check package → walk _SCREEN_FINGERPRINTS → return state const

Navigation:
    navigate_to_swipe()      → tap tab_explore + sleep(1.5)
    navigate_to_chat_list()  → tap tab_dashboard + sleep(1.5)
    navigate_to_likes()      → _get_like_inner_tab_bounds() + tap + sleep(1.5)

Queries (called by tasks via Platform ABC):
    get_matched_friends()    → [MatchedFriend(bounds)] via _get_all_matched_friend_cards()
    get_liked_profiles()     → [LikedProfile(bounds)] via thumb_photo_imageview
    get_chat_candidates()    → [ChatCandidate] — matched(is_matched=True) + unread rows

Private UI queries (NOT called by tasks):
    _is_app_open()                   → checks package attribute on any node
    _get_like_inner_tab_bounds()     → finds "Like" tab in dashboard (y_min < 300 guard)
    _get_all_matched_friend_cards()  → expire_progressbar → walk to clickable container
    _get_chat_list_rows()            → last_msg_textview → walk to clickable container
    _find_clickable_ancestor(node, parent_map, max_depth=6)  — shared walk helper

Deduplication in card/row finders: set of (x_min, y_min) tuples prevents double-counting.
```

### ClipCritic (`clip_critic/critic.py`)

```
evaluate(image_path) → CriticResult(score: float 0-100, liked: bool)
    Loads CLIP ViT-B/32 + classifier.pkl (LogisticRegression on 512-D embeddings)
    Lazy-loads on first call. Fail-closed: any exception → CriticResult(0.0, False)
    threshold controlled by config.ai.clip_threshold (default 0.6)

Training: clip_critic/trainer.py
    Reads labeled_data/{liked,disliked}/ directories
    Embeds all images → fits LogisticRegression → saves classifier.pkl
```

### HarvestService (`profile_db/harvest.py`)

```
harvest_profile(screenshot_path) → profile_id | None
    Reads: NAME_IDS, AGE_IDS, BIO_IDS, ANSWER_IDS from vision.get_node_text()
    Writes: ProfileStore.upsert() + add_photo() if screenshot provided
    profile_id = make_profile_id(name, age, "meeff") — deterministic 16-char hash

harvest_chat_contact() → profile_id | None
    Reads name from toolbar_title / title_textview / nickname_textview
    Creates minimal profile record (name only)

record_decision(profile_id, liked: bool)  — updates ProfileStore
record_message(profile_id, direction, text)  — appends to ProfileStore
get_profile(profile_id) → dict | None
```

### AIService + MessageGenerator

```
AIService: thin Claude API wrapper
    chat_reply(system, messages) → str  — calls claude-haiku-4-5 (configurable)

MessageGenerator Protocol:
    generate(messages: list[dict], profile: dict | None) → str | None

AIMessageGenerator implements MessageGenerator:
    if no "sent" messages in history: return random opener from config
    else: build Anthropic message list (sent→assistant, received→user) → AIService.chat_reply()
```

---

## 8. BotContext — Dependency Injection Container

Every task receives a single `BotContext` instance. Tasks import nothing from services directly.

```python
@dataclass
class BotContext:
    adb:               AdbService          # device I/O
    vision:            VisionService       # XML parsing
    ai:                AIService           # Claude API
    critic:            ClipCritic         # CLIP scorer
    config:            dict               # parsed config.json
    platform:          Platform           # MeeffPlatform (or future Instagram)
    clip_enabled:      bool               # gate for CLIP profile scoring
    chat_enabled:      bool               # gate for AI chat replies (separate from clip)
    status:            StatusBar | None   # terminal UI (optional)
    harvest:           HarvestService | None  # profile DB (optional)
    message_generator: MessageGenerator | None  # chat reply gen (optional)
```

**clip_enabled vs chat_enabled**: These are independent flags. Disabling CLIP scoring
(like everyone) does not disable chat replies, and vice versa. Both read from `ai` config block.

---

## 9. Timer System

```
PeriodicScheduler:
    _last: dict[str, float]   — maps timer name → last reset timestamp
    is_due(name, interval_secs) → time.time() - _last.get(name, 0.0) >= interval
    reset(name)               — sets _last[name] = time.time()
    time_remaining(name, interval) → float seconds until due

Active timers (registered in main.py, displayed by StatusBar):
    "chat_queue"  — interval: chat_queue_interval_minutes (default 5 min)
                    triggers ChatQueueTask to navigate to chat list + process inbox
    "likes"       — interval: likes_check_interval_minutes (default 10 min)
                    same trigger path as chat_queue (ChatQueueTask._any_timer_due)

Both timers are reset on startup (scheduler.reset()) so the first fire is
after the configured interval, not immediately.

ChatQueueTask._any_timer_due() checks both timers — either one triggers navigation.
_reset_due_timers() resets only the ones that are currently due (not both blindly).
```

---

## 10. File / Module Map

```
meeff/
├── main.py                    Entry point. build_bot() wires all services and tasks.
├── config.json                All runtime configuration. Loaded by AdbService.__init__.
├── src/
│   ├── emulator.py            Emulator lifecycle (is_running, start). Independent of bot.
│   ├── adb_service.py         All ADB I/O. _invoke_adb() is the single subprocess call site.
│   ├── vision_service.py      Pure XML parser. No app knowledge.
│   ├── ai_service.py          Claude API thin wrapper.
│   ├── core/
│   │   ├── orchestrator.py    Main tick loop. App-agnostic.
│   │   ├── task.py            Task ABC with priority, is_eligible, needs_navigation, run.
│   │   ├── context.py         BotContext dataclass.
│   │   ├── states.py          All state string constants + DIALOG_STATES set.
│   │   ├── platform.py        Platform ABC + MatchedFriend, LikedProfile, ChatCandidate dataclasses.
│   │   ├── scheduler.py       PeriodicScheduler (named timers).
│   │   ├── status_bar.py      Terminal UI with ANSI scroll region. Daemon thread.
│   │   └── message_generator.py  MessageGenerator Protocol + AIMessageGenerator.
│   ├── platforms/
│   │   └── meeff.py           MeeffPlatform. All Meeff resource-id knowledge.
│   └── tasks/
│       ├── dialog_task.py     Priority 100. Dismiss ads/overlays.
│       ├── matched_profile_task.py  Priority 60. Harvest + open match chat.
│       ├── chat_task.py       Priority 50. Manage one conversation.
│       ├── chat_queue_task.py Priority 15. Timer-driven inbox worker.
│       ├── like_page_task.py  Priority 10. Process incoming likes page.
│       ├── profile_task.py    Priority 5.  CLIP score + like/nope.
│       ├── swipe_task.py      Priority 5.  Open profile card.
│       └── recovery_task.py   Priority 1.  App launch + safe escape.
├── clip_critic/
│   ├── critic.py              ClipCritic: CLIP ViT-B/32 + LogisticRegression.
│   └── trainer.py             Train classifier from labeled_data/.
├── profile_db/
│   ├── store.py               ProfileStore: SQLite. Tables: profiles, photos, chat_messages.
│   └── harvest.py             HarvestService: screen scrape → ProfileStore writes.
├── tests/
│   ├── test_vision_service.py Tests state detection via MeeffPlatform + mock ADB.
│   └── test_lock_state.py     Tests AdbService lock detection.
└── page_data/                 Static XML dumps for testing (18 screen states).
```

---

## 11. Design Invariants

These are the structural rules the design relies on. Violating them breaks the bot silently.

1. **One task per tick.** The `break` in the orchestrator loop after the first eligible task is load-bearing. Do not remove it or make tasks call other tasks.

2. **Tasks never import services.** All service access is via `ctx`. Tasks receive `BotContext`, period. This is what makes the platform abstraction work.

3. **VisionService knows nothing about Meeff.** No resource-id strings, no state detection, no app-specific queries. All of that is in MeeffPlatform.

4. **State strings are constants from `states.py`.** Never compare against raw string literals in task code. A renamed state is a one-file change.

5. **MeeffPlatform private methods (`_get_*`) are not called by tasks.** Tasks only call Platform ABC methods. Private methods are implementation details of the platform.

6. **`detect_state()` always calls `refresh_screen_data()` first.** The XML cache must be fresh before fingerprinting. This costs ~500ms per tick but ensures correctness.

7. **ChatTask session state is per-conversation, reset in `_leave()`.** Fields `_waiting_since`, `_profile_id`, `_msg_count_at_send`, `_recorded_msg_count` are only valid between `is_eligible()` returning True and `_leave()` being called. A dialog interrupting ChatTask does NOT call `_leave()`.

8. **`clip_enabled` and `chat_enabled` are independent.** Disabling one does not disable the other. `ProfileEvalTask` gates on `clip_enabled`. `ChatTask` gates on `chat_enabled`.

9. **`RecoveryTask.is_eligible()` always returns True.** It only wins a tick when ALL other tasks return False from `is_eligible()`. It is the true catch-all.

10. **Both timers prime on startup.** `scheduler.reset("chat_queue")` and `scheduler.reset("likes")` are called in `build_bot()` so the bot starts swiping immediately rather than going to inbox first.

---

## 12. Extension Points — How to Add a New Platform (e.g. Instagram)

1. Create `src/platforms/instagram.py` subclassing `Platform`.
2. Implement: `app_package`, `detect_state()`, `navigate_to_swipe()`, `navigate_to_chat_list()`, `navigate_to_likes()`, `get_matched_friends()`, `get_liked_profiles()`, `get_chat_candidates()`.
3. In `detect_state()`: use `vision.collect_resource_ids()` and `vision.collect_content_descs()` with Instagram-specific fingerprints. Return the same state constants from `states.py` where they apply; add new ones if Instagram has unique screens.
4. In `main.py`: replace `MeeffPlatform(adb, vision)` with `InstagramPlatform(adb, vision)`.
5. Zero changes to any task file. Zero changes to Orchestrator. Zero changes to VisionService.

**Adding a new task:**
1. Create `src/tasks/my_task.py` subclassing `Task`.
2. Set `priority` (int). Implement `is_eligible(state)` and `run(ctx, state)`.
3. If scheduled: override `needs_navigation(state)` and `navigate_to(ctx)`.
4. Register in `main.py` task list. Orchestrator sorts by priority automatically.
