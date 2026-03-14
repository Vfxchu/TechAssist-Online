# TechAssist — Test Scenarios, Bug Checklist & Implementation Plan

---

## PART 1 — TEST SCENARIOS

### TC-001 — New Ticket Creation
**Scenario:** User opens app and submits a new issue  
**Input:** "My laptop is not connecting to WiFi"  
**Expected:**
- New ticket created with status: Open
- Ticket ID assigned (TKT-XXXX format)
- AI responds with first diagnostic question (not a fix)
- Category auto-assigned as: Network
- Severity auto-assigned based on description

**Pass Condition:** Ticket exists in DB, AI asks one question, no fix suggested yet

---

### TC-002 — AI Diagnostic Flow (One Question at a Time)
**Scenario:** Verify AI never asks more than one question per message  
**Input:** User sends any problem description  
**Expected:**
- AI message contains exactly one question
- AI does not suggest any fix in this phase
- Each follow-up response triggers exactly one more question

**Pass Condition:** 5 consecutive AI responses during diagnosis phase each contain only one question

---

### TC-003 — Screenshot Upload
**Scenario:** User uploads a screenshot mid-conversation  
**Input:** Image file (PNG/JPG) attached to a message  
**Expected:**
- File saved to UPLOAD_DIR on server
- File path stored on message record in DB
- AI acknowledges the screenshot and references it in next response
- Ticket screenshot list updated

**Pass Condition:** File present on disk, path in DB, AI references image content

---

### TC-004 — Tiered Fix Suggestions (Simple to Critical)
**Scenario:** After diagnosis, verify AI suggests fixes in correct order  
**Flow:**
1. Complete diagnosis phase
2. User clicks "Still not working" repeatedly
3. Verify fix tier escalates each time

**Expected order:**
- Response 1: Restart / basic action (Tier 1)
- Response 2: Settings change (Tier 2)
- Response 3: Reinstall / update (Tier 3)
- Response 4: System-level fix (Tier 4)
- Response 5: Critical / advanced (Tier 5)
- Response 6: Escalation offer (Tier 6)

**Pass Condition:** Each successive suggestion is more advanced than the previous

---

### TC-005 — Live Documentation Fetch
**Scenario:** AI fetches real documentation when suggesting a fix  
**Input:** Issue involving a known software (e.g. Windows network reset)  
**Expected:**
- AI response includes a direct URL to official documentation
- URL is valid and reachable
- AI references specific steps from the fetched page
- Version-specific doc fetched if OS version was gathered during diagnosis

**Pass Condition:** Response contains working URL from microsoft.com / apple.com / vendor site

---

### TC-006 — Step Confirmation Buttons
**Scenario:** Action buttons appear after each fix suggestion  
**Expected:**
- Three buttons rendered after every AI fix suggestion: "That fixed it" / "Still not working" / "Show me more detail"
- "That fixed it" → ticket status changes to Resolved
- "Still not working" → failed_attempts counter increments, next suggestion triggered
- "Show me more detail" → AI expands current fix with substeps

**Pass Condition:** All three buttons functional, DB updated correctly on each click

---

### TC-007 — Ticket Resolved Flow
**Scenario:** User confirms issue is fixed  
**Input:** User clicks "That fixed it"  
**Expected:**
- Ticket status updated to Resolved
- resolved_at timestamp set
- Solution text saved to ticket record
- Solution also saved to solutions memory DB
- Satisfaction prompt shown to user (thumbs up / thumbs down)

**Pass Condition:** All five conditions met, record updated in DB

---

### TC-008 — Escalation to Human Agent
**Scenario:** AI cannot resolve after MAX_FAILED_ATTEMPTS  
**Input:** User clicks "Still not working" 5 times  
**Expected:**
- After 5th failure, AI offers to escalate
- User confirms escalation
- Ticket status changes to In Progress
- assigned_to field populated
- Full ticket history visible to agent

**Pass Condition:** Escalation triggered at exactly MAX_FAILED_ATTEMPTS, all fields updated

---

### TC-009 — Solution Memory Match
**Scenario:** Same issue raised again after being resolved previously  
**Input:** New ticket with same OS + software + issue keywords as a resolved ticket  
**Expected:**
- AI checks solutions DB before web search
- If match confidence above threshold, AI suggests previous solution first
- AI mentions this was a previously successful solution

**Pass Condition:** Solution memory hit on matching ticket, web search skipped or secondary

---

### TC-010 — Auto-Categorization Accuracy
**Scenario:** Verify AI assigns correct category on ticket creation  
**Test inputs and expected categories:**

| Input | Expected Category |
|---|---|
| "WiFi not connecting" | Network |
| "Laptop screen cracked" | Hardware |
| "Excel keeps crashing" | Software |
| "Can't log into my account" | Access |
| "Printer not found" | Hardware |
| "VPN won't connect" | Network |
| "Microsoft Teams audio not working" | Software |

**Pass Condition:** 6 out of 7 correctly categorized

---

### TC-011 — Severity Detection
**Scenario:** Verify AI assigns correct severity  
**Test inputs and expected severities:**

| Input | Expected Severity |
|---|---|
| "My mouse scroll is a bit slow" | Low |
| "Outlook is loading slowly" | Medium |
| "I cannot access any files on the server" | High |
| "Production system is completely down, no one can work" | Critical |

**Pass Condition:** All 4 correctly assigned

---

### TC-012 — Progress Tracker UI
**Scenario:** Progress bar updates at correct stages  
**Expected stages in order:**
- Diagnosing (initial state)
- Understanding (after first user reply)
- Suggesting (after diagnosis complete, first fix shown)
- Resolving (after user says "Show me more detail")
- Closed (after resolved or escalated)

**Pass Condition:** Progress bar stage matches conversation phase at all times

---

### TC-013 — Analytics Dashboard
**Scenario:** Dashboard shows accurate data  
**Expected:**
- Total ticket count matches DB record count
- Resolution rate = resolved tickets / total tickets × 100
- Average resolution time calculated correctly
- Top issues list sorted by frequency descending
- Satisfaction score = thumbs up / (thumbs up + thumbs down) × 100

**Pass Condition:** All metrics match raw DB data

---

### TC-014 — Version-Aware Documentation
**Scenario:** AI fetches docs specific to user's OS version  
**Flow:**
1. User says "I'm on Windows 10"
2. AI gathers this during diagnosis
3. Fix suggestion fetches Windows 10 specific docs (not Windows 11)

**Pass Condition:** Search query includes OS version, fetched URL is version-specific

---

### TC-015 — Multi-Turn Context (No Repeat Questions)
**Scenario:** AI never asks a question already answered  
**Flow:**
1. User says "I'm on MacOS Ventura, 14-inch MacBook Pro"
2. Conversation continues for 10+ turns

**Expected:** AI never asks "what OS are you on?" or "what device?" again

**Pass Condition:** Zero repeated questions across 10-turn conversation

---

## PART 2 — BUG CHECKLIST

### Backend Bugs to Watch

| # | Bug | Where to Check |
|---|---|---|
| B-001 | Claude returns malformed JSON during auto-categorization — backend crashes on parse | claude.py — wrap JSON parse in try/except, fallback to "Other" / "Medium" |
| B-002 | Failed attempts counter not persisting between requests | tickets router — confirm failed_attempts written to DB not just in-memory |
| B-003 | Screenshot path stored as absolute path — breaks on server restart | messages.py — store relative path from UPLOAD_DIR only |
| B-004 | Conversation history not passed to Claude on every message — AI loses context | claude.py — confirm full message history fetched from DB and sent each call |
| B-005 | Tavily/Serper API key missing in .env — search silently returns nothing | search.py — raise clear error if API key not set, do not fail silently |
| B-006 | Solution memory search running on every message not just first suggestion | solutions.py — gate the search to trigger once per ticket not per message |
| B-007 | resolved_at not set when ticket resolved via "That fixed it" button | tickets router PATCH — confirm resolved_at = datetime.utcnow() on resolve |
| B-008 | CORS not configured for frontend port — all requests blocked | main.py — confirm allow_origins includes React dev server URL |
| B-009 | Multipart file upload not handled — screenshot upload returns 422 | main.py — confirm python-multipart installed and endpoint uses File() |
| B-010 | SQLAlchemy async session not closed after request — connection pool leak | database.py — confirm yield session with try/finally close |

### Frontend Bugs to Watch

| # | Bug | Where to Check |
|---|---|---|
| B-011 | Action buttons (Fixed / Didn't work / More detail) render on every message not just AI fix suggestions | Message.jsx — buttons should only show when message role is assistant AND phase is suggesting |
| B-012 | Screenshot preview not shown before send — user cannot confirm correct file | ScreenshotUpload.jsx — add local FileReader preview before upload |
| B-013 | Chat does not auto-scroll to latest message | Chat.jsx — useEffect with scrollIntoView on messages array change |
| B-014 | Progress tracker does not update when phase changes | ProgressTracker.jsx — subscribe to ticket status from API or parent state |
| B-015 | Ticket list does not refresh after new ticket created | TicketList.jsx — refetch on navigation or use state lifted to parent |
| B-016 | API errors shown as blank screen — no error message to user | client.js — global axios error interceptor showing user-friendly message |
| B-017 | Long AI responses not line-broken — wall of text renders | Message.jsx — render with whitespace-pre-wrap or markdown parser |
| B-018 | Satisfaction buttons (thumbs) not disabled after one click | ActionButtons or Ticket.jsx — disable after first submission |

---

## PART 3 — ANTIGRAVITY KNOWLEDGE ITEM

Paste this exactly into Antigravity as the Knowledge Item for TechAssist:

---

# TechAssist — AI IT Helpdesk Knowledge Base

## What This Application Is
TechAssist is an AI-powered IT helpdesk web application. It replaces traditional human-first IT support with a diagnostic AI chat that understands the issue fully before suggesting any fix. Built for internal IT teams and end users.

## Tech Stack — Final and Confirmed
- **Language:** Python (backend), JavaScript (frontend) — no TypeScript
- **Backend Framework:** FastAPI (async)
- **Frontend Framework:** React with Vite
- **Styling:** Tailwind CSS
- **AI:** Anthropic Claude API (claude-sonnet-4-20250514)
- **Web Search:** Tavily API
- **Database:** SQLite via SQLAlchemy (async)
- **File Storage:** Local filesystem (UPLOAD_DIR env variable)

## Three Database Models
1. Ticket — id, title, category, severity, priority, status, user_id, assigned_to, created_at, updated_at, resolved_at, solution, satisfaction, failed_attempts
2. Message — id, ticket_id, role, content, screenshot_path, created_at
3. Solution — id, category, os, software, issue_summary, solution_steps, source_ticket_id, success_count, created_at

## AI Behavior — Non-Negotiable Rules
- Phase 1 DIAGNOSE: Ask one question at a time. Never suggest a fix until device, OS, software, error message, timeline, and what was already tried are all collected.
- Phase 2 CATEGORIZE: Output JSON silently with category, severity, suggested_title after diagnosis.
- Phase 3 SUGGEST: Fixes go Tier 1 (restart) → Tier 6 (escalate). One tier per user response. Each fix includes official documentation URL.
- Phase 4 RESOLVE: Output JSON with status resolved or escalate when confirmed.

## Ticket Status Flow
Open → In Progress → Pending User → Resolved → Closed

## Escalation Rule
After failed_attempts reaches MAX_FAILED_ATTEMPTS (default 5), AI offers escalation to human agent.

## Solution Memory Rule
On every new ticket, check solutions DB for matching category + OS + software before calling Tavily search.

## API Endpoints (10 total)
POST /tickets, GET /tickets, GET /tickets/{id}, PATCH /tickets/{id}, POST /tickets/{id}/messages, POST /tickets/{id}/screenshots, POST /tickets/{id}/resolve, POST /tickets/{id}/escalate, POST /tickets/{id}/satisfaction, GET /analytics/summary, GET /analytics/common-issues, GET /solutions/search

## Environment Variables
ANTHROPIC_API_KEY, SEARCH_API_KEY, DATABASE_URL, UPLOAD_DIR, MAX_FAILED_ATTEMPTS, SOLUTION_MATCH_THRESHOLD

## Out of Scope — Phase 1
Authentication, email/SMS notifications, mobile app, RAG over internal docs, screen recording, screenshot annotation, YouTube suggestions, multi-language support

---

## PART 4 — CLAUDE CODE IMPLEMENTATION PLAN PROMPT

Paste this into Claude Code after the build is complete to generate the implementation plan:

---

```
Read PRD.md fully. Then create a file called IMPLEMENTATION_PLAN.md with the following structure:

## Phase 1 — Backend Foundation
List every file to create in backend/ with one-line description of what each does.
Estimated time per file.

## Phase 2 — AI Integration
Detail exactly how claude.py implements the four-phase system prompt.
Show the exact JSON structure Claude must return for categorization and resolution.
Show how conversation history is assembled and passed on every API call.

## Phase 3 — Search Integration
Detail how search.py calls Tavily API.
Show how the version string from diagnosis is injected into the search query.
Show how the fetched page content is summarized and passed back to Claude.

## Phase 4 — Frontend
List every component with its props, state, and which API endpoint it calls.
Specify exactly when ActionButtons renders (only after AI fix suggestions, not diagnostic messages).
Specify exactly how ProgressTracker determines current phase.

## Phase 5 — Testing
Map every test case from TEST_SCENARIOS.md to the exact file and function being tested.
For each bug in the bug checklist, specify the exact line or function where the fix must be applied.

## Phase 6 — Known Risks
List the top 5 failure points in this system with mitigation for each.

Do not hallucinate. Only include what is in the PRD. Mark anything uncertain as [CONFIRM].
```