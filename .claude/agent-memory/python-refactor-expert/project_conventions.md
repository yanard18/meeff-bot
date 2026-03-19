---
name: meeff project conventions
description: Coding conventions, architecture patterns, and refactoring decisions for the meeff bot codebase
type: project
---

Architecture: Platform/Task/Orchestrator pattern. Platform subclasses hold all app-specific UI knowledge; Task subclasses handle one logical activity; Orchestrator runs the tick loop. BotContext is the single shared service container passed to every Task.run().

Established conventions:
- No section-header banners (`# ---`) — class docstrings and method docstrings are sufficient.
- No alignment padding on assignment operators (E221); plain single-space assignments throughout.
- `_DIALOG_STATES` set in dialog_task.py is the canonical pattern for state membership checks.
- ChatTask extension hooks (`# Extension hooks` banner) are intentionally preserved — they signal a subclassing contract for Phase 1+ AI chat.

Key refactoring decisions made (2026-03-19, status_line / scheduler / orchestrator review):
- `status_line.py`: removed unused `import time` (module never calls time directly — all timing delegated to PeriodicScheduler).
- `status_line.py`: added explicit `key=lambda e: e[0]` to `sorted()` in `_render` to make sort criterion (remaining time) unambiguous rather than relying on tuple-comparison position.
- `status_line.py`: removed E221 alignment padding on module-level constants (`_RED`, `_YELLOW`, `_RESET`, `_URGENT_SECS`, `_WARNING_SECS`) per established project convention.
- `status_line.py` stat locals (`p`, `lk`, `n`): REJECTED — inlining three `.get()` calls into the f-string would hurt readability more than the locals hurt clarity.
- `orchestrator.py` `sys.exit()` in `verify_system`: REJECTED — class is the top-level CLI driver; raising instead adds ceremony with no practical gain.

Key refactoring decisions made (2026-03-19):
- `get_matched_friends` / `get_liked_profiles` in MeeffPlatform: removed redundant count-check-before-bounds-query. The bounds call already returns None when nothing is present; the count call was a wasteful second XML parse.
- RecoveryTask.is_eligible: removed two inline comments that duplicated the class docstring. `return True` is self-evident in this context.
- `scoring_enabled` on BotContext semantically conflates CLIP scoring with "AI enabled" — this is a known mismatch but fixing it requires interface changes; deferred.

Print/logging convention (established 2026-03-19, print refactor pass):
- All print prefixes use a noun-based component name in brackets: `[Orchestrator]`, `[Dialog]`, `[Recovery]`, `[Swipe]`, `[Profile]`, `[ChatList]`, `[Likes]`, `[Chat]`.
- Exception: `verify_system()` in orchestrator uses sentinel prefixes `[*]`/`[!]`/`[+]` for the one-time startup sequence. This is intentional — visually distinct from the running loop.
- Do NOT print a count/status message unconditionally and then follow it with a more specific message for the empty-list case. Gate the count print on the non-empty branch.
- Do NOT use trailing `\n` inside print() calls — let the loop structure create visual separation.

**Why:** align with PEP 8 and the project's Golden Rule (value over volume).
**How to apply:** When reviewing future changes, reject alignment padding and section banners unless there are genuinely many heterogeneous methods that need visual grouping.
