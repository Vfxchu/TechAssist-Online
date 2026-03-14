# TechAssist — AI-Powered IT Helpdesk

AI-first IT support chat that diagnoses issues through structured questioning, suggests fixes from simple to critical, fetches live documentation, and tracks everything in a persistent ticket system.

---

## Quick Start

### 1. Create your `.env` file

```bash
cd techassist
cp .env.example backend/.env
```

Edit `backend/.env` and fill in your keys:

```
ANTHROPIC_API_KEY=sk-ant-...
SEARCH_API_KEY=tvly-...        # Tavily API key (https://tavily.com) — or a Serper key
```

### 2. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Start the backend

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API is now live at `http://localhost:8000`.
Swagger docs: `http://localhost:8000/docs`

### 4. Install frontend dependencies

```bash
cd frontend
npm install
```

### 5. Start the frontend

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## Project Structure

```
techassist/
├── backend/
│   ├── main.py               FastAPI app, CORS, startup
│   ├── config.py             Environment variable loading
│   ├── database.py           SQLAlchemy engine + session
│   ├── schemas.py            Pydantic request/response schemas
│   ├── models/
│   │   ├── ticket.py         Ticket ORM model
│   │   ├── message.py        Message ORM model
│   │   └── solution.py       Solution memory ORM model
│   ├── services/
│   │   ├── claude.py         Claude API + 4-phase system prompt + search loop
│   │   ├── search.py         Web search (Tavily / Serper fallback)
│   │   └── solutions.py      Solution memory match + save logic
│   ├── routers/
│   │   ├── tickets.py        Ticket CRUD endpoints
│   │   ├── messages.py       Chat + screenshot upload endpoints
│   │   ├── analytics.py      Dashboard summary endpoints
│   │   └── solutions.py      Solution search endpoint
│   ├── uploads/              Screenshot files (auto-created)
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       ├── App.jsx            React Router setup
│       ├── api/client.js      Typed API functions (axios)
│       ├── pages/
│       │   ├── Home.jsx       New ticket entry + recent tickets
│       │   ├── Ticket.jsx     Active ticket chat view
│       │   └── Admin.jsx      Analytics dashboard
│       └── components/
│           ├── Chat.jsx           Message feed + input bar
│           ├── Message.jsx        Message bubble renderer
│           ├── TicketPanel.jsx    Ticket metadata sidebar
│           ├── ProgressTracker.jsx Diagnostic phase bar
│           ├── ScreenshotUpload.jsx File upload with drag-drop
│           ├── ActionButtons.jsx  Fixed / Not working / More detail
│           ├── TicketList.jsx     Recent tickets list
│           └── Dashboard.jsx      Analytics charts + stats
│
├── .env.example
└── README.md
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/tickets` | Create new ticket |
| GET | `/api/v1/tickets` | List tickets (filter by `?status=`) |
| GET | `/api/v1/tickets/{id}` | Get ticket with all messages |
| PATCH | `/api/v1/tickets/{id}` | Update title, status, severity, priority |
| POST | `/api/v1/tickets/{id}/messages` | Send user message, get AI response |
| POST | `/api/v1/tickets/{id}/screenshots` | Upload screenshot (multipart) |
| POST | `/api/v1/tickets/{id}/resolve` | Mark ticket resolved |
| POST | `/api/v1/tickets/{id}/escalate` | Escalate to human agent |
| POST | `/api/v1/tickets/{id}/satisfaction` | Submit thumbs up (1) or down (-1) |
| GET | `/api/v1/analytics/summary` | Dashboard summary stats |
| GET | `/api/v1/analytics/common-issues` | Top 10 issue categories |
| GET | `/api/v1/solutions/search?q=` | Search solution memory |

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `SEARCH_API_KEY` | Recommended | Tavily or Serper key for live doc search |
| `DATABASE_URL` | No | Defaults to `sqlite:///./techassist.db` |
| `UPLOAD_DIR` | No | Defaults to `./uploads` |
| `MAX_FAILED_ATTEMPTS` | No | Escalation trigger threshold (default: 5) |
| `SOLUTION_MATCH_THRESHOLD` | No | Memory match confidence (default: 0.75) |
| `CORS_ALLOWED_ORIGINS` | No | Defaults to localhost:5173,localhost:3000 |

---

## How It Works

1. **User** opens Home, types their issue, clicks "Start Support Chat"
2. **Ticket** is created in SQLite, user is redirected to the chat page
3. **Chat** sends the issue to Claude via `POST /tickets/{id}/messages`
4. **Claude (Phase 1)** asks one focused diagnostic question at a time
5. **Claude (Phase 2)** silently outputs category/severity JSON — backend updates the ticket
6. **Claude (Phase 3)** suggests fixes in Tier 1→6 order. When it needs docs, it outputs `[SEARCH: query]` — backend fetches live results via Tavily and injects them, then re-calls Claude
7. **User** clicks "That fixed it" / "Still not working" / "Show me more detail"
8. **Claude (Phase 4)** outputs `{"status": "resolved"}` → ticket is closed and solution saved to memory
9. **User** rates the resolution with thumbs up/down
10. **Future tickets** with similar profile get the saved solution suggested first
