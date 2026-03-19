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

Key refactoring decisions made (2026-03-19):
- `get_matched_friends` / `get_liked_profiles` in MeeffPlatform: removed redundant count-check-before-bounds-query. The bounds call already returns None when nothing is present; the count call was a wasteful second XML parse.
- RecoveryTask.is_eligible: removed two inline comments that duplicated the class docstring. `return True` is self-evident in this context.
- `scoring_enabled` on BotContext semantically conflates CLIP scoring with "AI enabled" — this is a known mismatch but fixing it requires interface changes; deferred.

**Why:** align with PEP 8 and the project's Golden Rule (value over volume).
**How to apply:** When reviewing future changes, reject alignment padding and section banners unless there are genuinely many heterogeneous methods that need visual grouping.
