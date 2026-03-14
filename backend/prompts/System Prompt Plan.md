# System Prompt Externalization Plan

**Status:** Plan only — not yet implemented
**Goal:** Move the hardcoded `SYSTEM_PROMPT` constant out of `claude.py` and into an external file so it can be edited and tuned (e.g., via Antigravity) without touching Python code.

---

## Current State

The system prompt lives as a multi-line string constant in `backend/services/claude.py` starting at line 24:

```python
SYSTEM_PROMPT = """You are Vishnu, an expert IT support specialist...
## PHASE 1 — DIAGNOSE
...
"""
```

**Problem:** Tuning the prompt requires editing Python code, redeploying, and restarting the server. No separation between prompt logic and application logic.

---

## Target State

```
backend/
  prompts/
    system_prompt.md       ← The live prompt file (edit this to tune Vishnu)
    System Prompt Plan.md  ← This document
  services/
    claude.py              ← Reads prompt from file at startup
```

---

## Implementation Steps

### Step 1 — Create `backend/prompts/system_prompt.md`

Move the content of `SYSTEM_PROMPT` verbatim into this file. No frontmatter, no wrapper — just the raw prompt text starting with `You are Vishnu...`.

### Step 2 — Modify `claude.py` to load from file

Replace the hardcoded constant with a file load at module startup:

```python
from pathlib import Path

_PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "system_prompt.md"

def _load_system_prompt() -> str:
    try:
        return _PROMPT_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raise RuntimeError(f"System prompt file not found: {_PROMPT_FILE}")

SYSTEM_PROMPT = _load_system_prompt()
```

**Why at module load (not per-request):** The prompt is the same for every request. Loading it once at startup is efficient and means a server restart is still required to pick up changes — which is intentional (prevents accidental mid-session prompt changes).

### Step 3 (Optional) — Hot-reload support

If hot-reload without restart is needed, change `_load_system_prompt()` to be called inside `process_chat_turn()` instead of at module level:

```python
def process_chat_turn(conversation_history, failed_attempts):
    system = _load_system_prompt()   # reloads from disk on every request
    ...
```

**Trade-off:** Adds a disk read per request (~0.1ms on SSD). Safe for development/tuning, but consider caching for production.

---

## Antigravity Integration Notes

Antigravity (the AI tuning platform referenced in the test scenarios doc) can:
- Version-control the prompt file via Git
- Run A/B evaluations by swapping `system_prompt.md` content
- Track which prompt version produced which outcomes in analytics

The key requirement from Antigravity's side is that the prompt is in a **plain text or markdown file** with no code around it. This plan satisfies that requirement.

---

## What Does NOT Change

- The 4-phase structure (DIAGNOSE → CATEGORIZE → SUGGEST → RESOLVE) stays in the prompt, not in code
- The `[SEARCH: ...]`, `[REQUEST_SCREENSHOT]`, and JSON output tokens stay defined in the prompt
- `claude.py` logic that parses those tokens is unaffected
- No API changes, no schema changes, no frontend changes

---

## Files to Edit When Implementing

| File | Change |
|------|--------|
| `backend/services/claude.py` | Replace `SYSTEM_PROMPT = """..."""` with file-load function |
| `backend/prompts/system_prompt.md` | New file — paste prompt content verbatim |

**Estimated effort:** ~15 minutes, zero risk of breaking anything.
