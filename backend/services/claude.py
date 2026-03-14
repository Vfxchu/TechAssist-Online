"""
Claude AI service.

Handles the full diagnostic chat turn including:
  - Calling Claude with the conversation history
  - The [SEARCH: query] loop (up to 3 searches per turn)
  - Parsing [REQUEST_SCREENSHOT], phase-2 category JSON, and phase-4 status JSON
  - Returning a clean display string with all tokens stripped
"""
import re
import json
import logging
from pathlib import Path
from anthropic import Anthropic
from config import get_settings
from services.search import search_web

logger = logging.getLogger(__name__)
settings = get_settings()

_TEMPERATURE = 0.3
_MAX_TOKENS = 1024

# ---------------------------------------------------------------------------
# System prompt — loaded from external file so it can be tuned without
# touching this code. File: backend/prompts/system_prompt.md
# ---------------------------------------------------------------------------

_PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "system_prompt.md"


def _load_system_prompt() -> str:
    try:
        return _PROMPT_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raise RuntimeError(
            f"System prompt file not found: {_PROMPT_FILE}. "
            "Create backend/prompts/system_prompt.md to configure the AI persona."
        )


SYSTEM_PROMPT = _load_system_prompt()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def process_chat_turn(
    conversation_history: list[dict],
    failed_attempts: int,
) -> dict:
    """
    Execute a full chat turn with the search loop.

    Args:
        conversation_history: list of {"role": "user"|"assistant", "content": str}
        failed_attempts: number of unsuccessful fix attempts so far on this ticket

    Returns a dict with keys:
        content              str   — cleaned text for display
        screenshot_requested bool
        escalation_recommended bool
        action_needed        str|None  — "resolved" | "escalate" | None
        category_data        dict|None — {category, severity, suggested_title}
        searches_performed   list[str]
    """
    system = SYSTEM_PROMPT
    if failed_attempts >= settings.max_failed_attempts - 1:
        system += (
            f"\n\nNOTE: {failed_attempts} fix attempts have failed on this ticket. "
            "You've exhausted the standard tiers. Escalate now — be straight with the user "
            "about what was tried, why it didn't work, and what needs to happen next."
        )

    MAX_SEARCH_LOOPS = 3
    working_messages = list(conversation_history)
    searches_performed: list[str] = []
    raw_response = ""

    for loop in range(MAX_SEARCH_LOOPS + 1):
        try:
            response = _get_client().messages.create(
                model=settings.anthropic_model,
                max_tokens=_MAX_TOKENS,
                temperature=_TEMPERATURE,
                system=system,
                messages=working_messages,
            )
            raw_response = response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            return {
                "content": f"Hit a snag on my end — give it a moment and try again. If it keeps happening, flag it to the team. (Error: {str(e)})",
                "screenshot_requested": False,
                "escalation_recommended": True,
                "action_needed": None,
                "category_data": None,
                "searches_performed": searches_performed,
            }

        # Check for a [SEARCH: ...] request
        search_match = re.search(r"\[SEARCH:\s*(.+?)\]", raw_response, re.IGNORECASE)
        if search_match and loop < MAX_SEARCH_LOOPS:
            query = search_match.group(1).strip()
            logger.info("Claude requested search: %s", query)
            searches_performed.append(query)

            results = search_web(query)

            # Append Claude's intermediate response to keep the conversation valid
            working_messages.append({"role": "assistant", "content": raw_response})

            # Build the injected search results block
            block = f"[SEARCH_RESULTS for: '{query}']\n\n"
            for i, r in enumerate(results[:4], 1):
                block += f"**Result {i}: {r.get('title', '')}**\n"
                if r.get("url"):
                    block += f"URL: {r['url']}\n"
                block += f"{(r.get('content') or '')[:600]}\n\n"
            block += "[/SEARCH_RESULTS]"

            working_messages.append({
                "role": "user",
                "content": (
                    f"{block}\n\n"
                    "Use these results to provide the user with specific, accurate instructions "
                    "including exact button/menu names and the documentation link."
                ),
            })
            continue  # loop back and call Claude again with the injected results

        break  # no search requested — we have the final response

    # --- Parse special tokens ---
    screenshot_requested = "[REQUEST_SCREENSHOT]" in raw_response

    # Phase-4 status JSON: {"status": "resolved", ...} or {"status": "escalate"}
    action_needed: str | None = None
    status_data = _extract_json(raw_response, required_key="status")
    if status_data:
        action_needed = status_data.get("status")   # "resolved" or "escalate"

    # Phase-2 category JSON: {"category": ..., "severity": ..., "suggested_title": ...}
    category_data: dict | None = None
    cat_data = _extract_json(raw_response, required_key="category")
    if cat_data:
        category_data = cat_data

    # --- Clean display content (strip all tokens and JSON blocks) ---
    display = raw_response
    display = re.sub(r"\[SEARCH:\s*.+?\]\n?", "", display, flags=re.IGNORECASE)
    display = display.replace("[REQUEST_SCREENSHOT]", "")
    display = re.sub(
        r"```json\s*\{[^}]*\"(?:status|category)\"[^}]*\}\s*```",
        "",
        display,
        flags=re.DOTALL,
    )
    display = re.sub(r'\{[^{}]*"(?:status|category)"[^{}]*\}', "", display)
    # Strip leftover search result injections (shouldn't appear in final turn but clean anyway)
    display = re.sub(r"\[SEARCH_RESULTS.*?\[/SEARCH_RESULTS\]", "", display, flags=re.DOTALL)
    display = display.strip()

    if screenshot_requested:
        display += "\n\n📎 **Please upload a screenshot** so I can see the issue directly."

    return {
        "content": display,
        "screenshot_requested": screenshot_requested,
        "escalation_recommended": (failed_attempts + 1) >= settings.max_failed_attempts,
        "action_needed": action_needed,
        "category_data": category_data,
        "searches_performed": searches_performed,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client() -> Anthropic:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set in .env")
    return Anthropic(api_key=settings.anthropic_api_key)


def _extract_json(text: str, required_key: str) -> dict | None:
    """Extract the first JSON object in *text* that contains *required_key*.
    Handles both bare JSON objects and fenced ```json ... ``` code blocks.
    """
    # First try fenced code block: ```json { ... } ```
    fenced_pattern = r"```json\s*(\{[^`]+\})\s*```"
    for m in re.finditer(fenced_pattern, text, re.DOTALL):
        try:
            data = json.loads(m.group(1))
            if required_key in data:
                return data
        except json.JSONDecodeError:
            pass

    # Fall back to bare JSON objects
    pattern = r"\{[^{}]*\"" + required_key + r"\"[^{}]*\}"
    match = re.search(pattern, text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None
