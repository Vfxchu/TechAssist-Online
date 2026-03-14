# Product Requirements Document
## AI-Powered IT Helpdesk — TechAssist

**Version:** 1.0  
**Stack:** Python (FastAPI) · React · Claude API (Anthropic) · SQLite  
**Purpose:** An AI-first IT support chat application that diagnoses technical issues through structured questioning, suggests fixes from simple to critical, fetches live documentation with screenshots, and tracks everything in a persistent ticket system.

---

## 1. Problem Statement

IT support teams and end users waste time describing problems to agents who ask repetitive questions and give generic fixes. There is no structured diagnostic flow, no reuse of past solutions, and no visibility into ticket resolution progress.

---

## 2. Goals

- AI diagnoses before it suggests — never jumps to solutions without understanding the issue
- Fixes are ordered from simplest (restart) to most critical (reinstall / escalate)
- Live documentation and button-level screenshots fetched from official sources
- Every conversation is a ticket — persisted, tracked, and closeable
- Escalation to human agent if AI cannot resolve after a defined number of steps

---

## 3. Users

| User | Description |
|---|---|
| End User | Employee or customer reporting a technical issue |
| IT Agent | Human who receives escalated tickets |
| Admin | Manages the system, views analytics dashboard |

---

## 4. Core Features

### 4.1 AI Diagnostic Chat

- User opens a new ticket and describes their issue in free text
- AI asks one focused question at a time to understand the issue fully
- AI never provides troubleshooting steps until it has gathered sufficient context
- Required context before suggesting fixes:
  - Device type (laptop / desktop / mobile)
  - Operating system and version
  - Software or application involved
  - Error message (exact text if any)
  - When the issue started
  - What changed recently
  - What the user has already tried
- If the AI needs visual context, it asks the user to upload a screenshot
- Once context is complete, AI transitions to the suggestion phase

### 4.2 Screenshot Upload

- User can upload screenshots at any point during the chat
- AI analyzes the screenshot using Claude vision capabilities
- AI describes what it sees in the screenshot and uses it to refine diagnosis
- Screenshots are stored and attached to the ticket record

### 4.3 Tiered Fix Suggestions

AI presents fixes in strict order from least to most disruptive:

| Tier | Type | Example |
|---|---|---|
| 1 | Basic | Restart the app or device |
| 2 | Settings | Change a configuration option |
| 3 | Software | Update, reinstall, or clear cache |
| 4 | Network/System | Flush DNS, reset network stack |
| 5 | Critical | OS-level fix, registry edit, full reinstall |
| 6 | Escalate | Hand off to human IT agent |

After each suggestion, user responds with one of:
- "This worked" → ticket resolved
- "Didn't work" → AI moves to next tier
- "Need help with this step" → AI provides more detail

### 4.4 Live Documentation Fetch

- When suggesting a fix, AI searches for the official documentation
- Search targets: Microsoft Docs, Apple Support, Google Help, software vendor docs
- Falls back to Stack Overflow or community forums if official docs not found
- AI extracts the relevant steps from the fetched page
- AI includes direct link to the documentation source
- Where available, AI fetches or references a screenshot showing the exact UI element (button, menu, setting) the user needs to interact with
- Search is version-aware — AI uses OS/software version gathered during diagnosis to fetch version-specific docs

### 4.5 Ticket System

Each conversation is a ticket with the following fields:

| Field | Type | Description |
|---|---|---|
| ticket_id | string | Auto-generated unique ID (e.g. TKT-0042) |
| title | string | Auto-generated summary of the issue |
| category | enum | Network / Hardware / Software / Access / Other |
| severity | enum | Low / Medium / High / Critical |
| status | enum | Open / In Progress / Pending User / Resolved / Closed |
| priority | enum | P1 / P2 / P3 / P4 |
| created_at | datetime | Ticket creation timestamp |
| updated_at | datetime | Last activity timestamp |
| resolved_at | datetime | When ticket was marked resolved |
| user_id | string | ID of the user who raised the ticket |
| assigned_to | string | Human agent ID if escalated (nullable) |
| messages | list | Full conversation history |
| screenshots | list | Uploaded file paths |
| solution | string | Final solution that resolved the issue (nullable) |
| satisfaction | int | 1 (thumbs up) or -1 (thumbs down) after close |

### 4.6 Auto-Categorization and Severity Detection

- On ticket creation, AI reads the initial message and assigns:
  - Category: Network / Hardware / Software / Access / Other
  - Severity: Low / Medium / High / Critical
- Severity rules:
  - Critical: production system down, data loss risk, security breach
  - High: user cannot perform primary work function
  - Medium: degraded performance or partial functionality
  - Low: cosmetic issue or minor inconvenience
- These can be overridden manually by IT agent

### 4.7 Solution Memory

- When a ticket is resolved, the solution is saved to the solutions database
- On future tickets, AI checks for similar past issues before searching the web
- If a match is found with confidence above threshold, AI suggests the previously successful solution first
- Match is based on: category + OS + software + issue keywords

### 4.8 Escalation to Human Agent

- AI tracks number of failed fix attempts per ticket
- After 5 failed suggestions, AI offers to escalate
- Escalation creates an assignment record and notifies the agent
- Agent sees full ticket history including all messages and screenshots
- Agent can continue the chat directly or resolve the ticket manually

### 4.9 Step Confirmation UI

After each fix suggestion, the chat displays three action buttons:
- "That fixed it" → marks ticket resolved
- "Still not working" → AI proceeds to next suggestion
- "Show me more detail" → AI expands with substeps and documentation

### 4.10 Progress Tracker

A visual progress bar is shown in the ticket view with stages:
- Diagnosing → Understanding → Suggesting → Resolving → Closed

### 4.11 Analytics Dashboard (Admin)

Metrics displayed:
- Total tickets (today / this week / this month)
- Resolution rate (% resolved by AI vs escalated)
- Average time to resolution
- Top 10 most common issues
- AI success rate per category
- User satisfaction score (thumbs up/down ratio)

### 4.12 User Satisfaction

- After ticket is closed, user sees a single prompt: "Did this solve your issue?"
- Two options: thumbs up / thumbs down
- Response stored on the ticket record

---

## 5. System Prompt Design

The Claude system prompt enforces the following behavior:

```
Phase 1 — DIAGNOSE
- Ask one question at a time
- Do not suggest any fix until all required context is collected
- If screenshot is needed, ask the user to upload one
- Required fields before proceeding: device, OS + version, software, error message, timeline, what was tried

Phase 2 — CATEGORIZE
- After diagnosis, output JSON with: category, severity, suggested_title
- This is parsed by the backend silently

Phase 3 — SUGGEST
- Present fixes in order from Tier 1 (simplest) to Tier 6 (escalate)
- For each fix, search for official documentation
- Include direct doc link and relevant screenshot if available
- After each suggestion, wait for user confirmation before proceeding

Phase 4 — RESOLVE
- When user confirms fix worked, output: { "status": "resolved", "solution": "..." }
- If user escalates, output: { "status": "escalate" }
```

---

## 6. API Endpoints (Backend)

| Method | Endpoint | Description |
|---|---|---|
| POST | /tickets | Create new ticket |
| GET | /tickets | List all tickets (with filters) |
| GET | /tickets/{id} | Get single ticket with full history |
| PATCH | /tickets/{id} | Update ticket status, severity, assignment |
| POST | /tickets/{id}/messages | Send a message in a ticket |
| POST | /tickets/{id}/screenshots | Upload a screenshot |
| POST | /tickets/{id}/resolve | Mark ticket as resolved |
| POST | /tickets/{id}/escalate | Escalate to human agent |
| POST | /tickets/{id}/satisfaction | Submit thumbs up/down |
| GET | /analytics/summary | Dashboard summary stats |
| GET | /analytics/common-issues | Top issues report |
| GET | /solutions/search | Search past solutions by keyword |

---

## 7. Data Models

### Ticket
```python
class Ticket(Base):
    id: str              # TKT-XXXX
    title: str
    category: str        # Network / Hardware / Software / Access / Other
    severity: str        # Low / Medium / High / Critical
    priority: str        # P1 / P2 / P3 / P4
    status: str          # Open / In Progress / Pending User / Resolved / Closed
    user_id: str
    assigned_to: str     # nullable
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime  # nullable
    solution: str          # nullable
    satisfaction: int      # nullable, 1 or -1
    failed_attempts: int   # count of unsuccessful fix suggestions
```

### Message
```python
class Message(Base):
    id: int
    ticket_id: str
    role: str            # user / assistant
    content: str
    screenshot_path: str  # nullable
    created_at: datetime
```

### Solution (memory store)
```python
class Solution(Base):
    id: int
    category: str
    os: str
    software: str
    issue_summary: str
    solution_steps: str
    source_ticket_id: str
    success_count: int
    created_at: datetime
```

---

## 8. Project Structure

```
techassist/
├── backend/
│   ├── main.py               # FastAPI app, CORS, startup
│   ├── routers/
│   │   ├── tickets.py        # Ticket CRUD endpoints
│   │   ├── messages.py       # Chat message endpoints
│   │   ├── analytics.py      # Dashboard endpoints
│   │   └── solutions.py      # Solution memory endpoints
│   ├── services/
│   │   ├── claude.py         # Claude API integration, system prompt
│   │   ├── search.py         # Web search + doc fetch (Tavily or Serper)
│   │   └── solutions.py      # Solution memory match logic
│   ├── models/
│   │   ├── ticket.py         # SQLAlchemy ticket model
│   │   ├── message.py        # SQLAlchemy message model
│   │   └── solution.py       # SQLAlchemy solution model
│   ├── database.py           # DB connection and session
│   ├── schemas.py            # Pydantic request/response schemas
│   └── config.py             # Environment variable loading
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chat.jsx              # Main chat interface
│   │   │   ├── Message.jsx           # Individual message bubble
│   │   │   ├── TicketPanel.jsx       # Ticket metadata sidebar
│   │   │   ├── ProgressTracker.jsx   # Diagnostic progress bar
│   │   │   ├── ScreenshotUpload.jsx  # File upload component
│   │   │   ├── ActionButtons.jsx     # Fixed/Didn't work/More detail
│   │   │   ├── TicketList.jsx        # List of all tickets
│   │   │   └── Dashboard.jsx         # Admin analytics view
│   │   ├── pages/
│   │   │   ├── Home.jsx              # New ticket entry
│   │   │   ├── Ticket.jsx            # Active ticket chat view
│   │   │   └── Admin.jsx             # Admin dashboard
│   │   ├── api/
│   │   │   └── client.js             # Axios API client
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js
├── .env.example
├── requirements.txt
└── README.md
```

---

## 9. Environment Variables

```
ANTHROPIC_API_KEY=sk-ant-...
SEARCH_API_KEY=...           # Tavily or Serper API key
DATABASE_URL=sqlite:///./techassist.db
UPLOAD_DIR=./uploads
MAX_FAILED_ATTEMPTS=5        # Before suggesting escalation
SOLUTION_MATCH_THRESHOLD=0.75
```

---

## 10. Tech Dependencies

### Backend
```
fastapi
uvicorn
sqlalchemy
pydantic
python-dotenv
anthropic
httpx
python-multipart     # file uploads
tavily-python        # or requests for Serper
```

### Frontend
```
react
react-router-dom
axios
tailwindcss
```

---

## 11. Out of Scope (v1)

- User authentication and login system
- Email or SMS notifications
- Mobile app
- Multi-language support
- SLA breach alerts
- RAG over internal documents (planned for v2)
- Screen recording upload (planned for v2)
- Screenshot annotation (planned for v2)
- YouTube video suggestions (planned for v2)