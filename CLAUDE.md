# CLAUDE.md - Core Engineering Protocol

## Operational Commands
- **Primary Execution:** `python main.py`
- **Verification:** Execute the program after every logic change to validate interactive performance.
- **Unit Testing:** Run `pytest` or `python -m unittest discover` before committing.
- **Git Workflow:** Perform atomic `git commit` operations for every verified change. Use imperative commit messages.

## The Golden Rule of Change
**Value over Volume.**
- Code must remain clean, robust, and simple.
- Prioritize maintainability over cleverness.
- If a requested change introduces complexity without significant gain in reliability or performance, do not implement it.
- Action: Inform the user if a change is deemed "not worth it" and provide a technical justification for the rejection.

## Technical Standards
- **State Management:** Always verify the application state before and after interacting with dynamic UI elements.
- **Synchronization:** Use explicit waits and element verification. Never assume an interface is ready based on timing alone.
- **DOM Stability:** Treat all DOM references as potentially stale after structural page updates; re-fetch elements to prevent runtime errors.
- **Error Handling:** Implement granular exception handling. Avoid generic "catch-all" blocks that mask underlying logic failures.

## Code Style & Architecture
- **Language:** Python (PEP 8 compliance required).
- **Design:** Favor composition and simple functions over deep inheritance or unnecessary abstractions.
- **Documentation:** Maintain concise docstrings for complex logic flows and state transitions.
