"""
TechAssist Backend Test Runner
Covers TC-001, TC-003, TC-006/007, TC-007, TC-008, TC-009, TC-013 + bug checks.

How we wire the DB for tests
─────────────────────────────
sqlite:///:memory: creates a brand-new empty DB for EVERY new connection.
database.py's SessionLocal opens a new connection per request, so tables
created via one connection are invisible to the next.  Fix: use a named
temp file so all connections share the same file-system DB.

We set DATABASE_URL to the temp-file path BEFORE importing anything so that
get_settings() (which is @lru_cache) picks it up on first call.

process_chat_turn is monkey-patched at the module level BEFORE the routers
import it, so no real Claude API call is ever made.
"""

# ── 0. Env vars FIRST — before any import ────────────────────────────────────
import os, sys, tempfile, pathlib

_db_file = pathlib.Path(tempfile.gettempdir()) / "techassist_test_runner.db"
if _db_file.exists():
    try:
        _db_file.unlink()
    except PermissionError:
        pass   # stale lock from a prior run; SQLite will still work

_DB_URL = f"sqlite:///{_db_file}"

os.environ["ANTHROPIC_API_KEY"] = "test-key"
os.environ["DATABASE_URL"]      = _DB_URL
os.environ["SEARCH_API_KEY"]    = ""

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# ── 1. Standard imports ───────────────────────────────────────────────────────
import io, struct, zlib, traceback

# ── 2. Result collector ───────────────────────────────────────────────────────
RESULTS = []

def record(label: str, passed: bool, http_code="", notes=""):
    RESULTS.append((label, passed, str(http_code), notes))
    icon = "PASS" if passed else "FAIL"
    code_str = f"  HTTP {http_code}" if http_code else ""
    print(f"  [{icon}] {label}{code_str}  {notes}")

# ─────────────────────────────────────────────────────────────────────────────
# STATIC ANALYSIS (reads source files directly — no import needed)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STATIC ANALYSIS ===\n")

import pathlib as _pl
_bp = _pl.Path(BACKEND_DIR)
static_bugs = []

def _text(rel):  return (_bp / rel).read_text(encoding="utf-8")
def _lines(rel): return _text(rel).splitlines()

# SA-1: schemas.py — SendMessageResponse (line ~26) uses TicketOut (line ~52)
# before TicketOut is defined in the same file.
schemas_lines = _lines("schemas.py")
smr_line = next((i+1 for i,l in enumerate(schemas_lines) if "class SendMessageResponse" in l), None)
to_line  = next((i+1 for i,l in enumerate(schemas_lines) if "class TicketOut" in l), None)

if smr_line and to_line and smr_line < to_line:
    msg = (f"schemas.py:{smr_line} — SendMessageResponse references TicketOut "
           f"(defined at line {to_line}) BEFORE that class is defined. "
           "Python raises NameError at class-body parse time — "
           "this is the direct cause of a 500 on POST /tickets/{id}/messages.")
    static_bugs.append(("SA-1", msg))
    print(f"  BUG (SA-1): {msg}")

# SA-2: services/claude.py — dead variable assignment
claude_text = _text("services/claude.py")
if "client = _get_client()" in claude_text and "_get_client().messages.create" in claude_text:
    msg = ("services/claude.py — 'client = _get_client()' result is never used; "
           "_get_client() is called again inside the loop at line 135. "
           "Minor waste, not a runtime crash.")
    static_bugs.append(("SA-2", msg))
    print(f"  NOTE (SA-2): {msg}")

# SA-3: database.py — connect_args hardcoded (SQLite only)
db_text = _text("database.py")
if '"check_same_thread": False' in db_text:
    guard_line = db_text.split('"check_same_thread"')[0].split("\n")[-1]
    if "if " not in guard_line:
        msg = ('database.py — connect_args={"check_same_thread": False} hardcoded for ALL '
               "DB URLs; will fail with PostgreSQL.")
        static_bugs.append(("SA-3", msg))
        print(f"  NOTE (SA-3): {msg}")

# SA-4: database.py — engine built at import time via @lru_cache settings
if "engine = create_engine" in db_text and "get_settings()" in db_text:
    msg = ("database.py — engine is created at MODULE-IMPORT TIME using get_settings(). "
           "Because get_settings() is @lru_cache, the engine URL is frozen on first import. "
           "If the module is imported before DATABASE_URL env var is set, the engine points "
           "at the wrong DB, causing 'no such table' OperationalError on every DB endpoint.")
    static_bugs.append(("SA-4", msg))
    print(f"  BUG (SA-4): {msg}")

if not static_bugs:
    print("  (no bugs found)")

print()

# ─────────────────────────────────────────────────────────────────────────────
# IMPORT TEST — test each module individually
# ─────────────────────────────────────────────────────────────────────────────
print("=== IMPORT TEST ===\n")

def _purge():
    for k in list(sys.modules.keys()):
        if any(k == m or k.startswith(m + ".") for m in
               ["config","database","models","schemas","services","routers","main"]):
            del sys.modules[k]

_purge()

import importlib as _il
import_errors = {}

for _mod in [
    "config", "database", "models.ticket", "models.message", "models.solution",
    "schemas", "services.search", "services.solutions", "services.claude",
    "routers.tickets", "routers.messages", "routers.analytics", "routers.solutions",
    "main",
]:
    for k in list(sys.modules.keys()):
        if k == _mod:
            del sys.modules[k]
    try:
        _il.import_module(_mod)
        print(f"  [PASS] import {_mod}")
    except Exception as e:
        import_errors[_mod] = str(e)
        print(f"  [FAIL] import {_mod} — {e}")

if import_errors:
    record("IMPORT all modules", False, "", f"Failed: {list(import_errors.keys())}")
else:
    record("IMPORT all modules", True, "", "All 14 modules imported OK")

print()

# ─────────────────────────────────────────────────────────────────────────────
# BUILD FASTAPI TEST CLIENT
# ─────────────────────────────────────────────────────────────────────────────
print("=== BUILDING TEST CLIENT ===\n")

FAKE_RESULT = {
    "content": "What device are you using?",
    "screenshot_requested": False,
    "escalation_recommended": False,
    "action_needed": None,
    "category_data": {
        "category": "Network",
        "severity": "Medium",
        "suggested_title": "WiFi issue",
    },
    "searches_performed": [],
}

_purge()
client = None
_build_error = None

try:
    import config as cfg_mod
    cfg_mod.get_settings.cache_clear()
    _s = cfg_mod.get_settings()
    print(f"  Settings DATABASE_URL = {_s.database_url!r}")

    import database as db_mod
    print(f"  Engine URL            = {db_mod.engine.url}")

    # Patch Claude BEFORE importing routers (so the mock is captured by routers.messages)
    import services.claude as claude_mod
    claude_mod.process_chat_turn = lambda history, failed_attempts: FAKE_RESULT

    import main as main_mod

    # Create all tables
    db_mod.init_db()
    print("  DB tables created.")

    from fastapi.testclient import TestClient
    client = TestClient(main_mod.app, raise_server_exceptions=False)
    print("  TestClient created.")

except Exception as exc:
    _build_error = exc
    print(f"  FAILED: {exc}")
    traceback.print_exc()

print()

if client is None:
    print("Cannot run endpoint tests — TestClient build failed.")
    tp = sum(1 for r in RESULTS if r[1])
    tf = sum(1 for r in RESULTS if not r[1])
    print(f"\n=== SUMMARY ===\nTotal: {tp} passed, {tf} failed")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Helper: build a minimal 1×1 red-pixel PNG in memory (no Pillow needed)
# ─────────────────────────────────────────────────────────────────────────────
def _make_tiny_png() -> bytes:
    def _chunk(name: bytes, data: bytes) -> bytes:
        body = name + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
    sig  = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    idat = _chunk(b"IDAT", zlib.compress(b"\x00\xFF\x00\x00"))
    iend = _chunk(b"IEND", b"")
    return sig + ihdr + idat + iend

TINY_PNG = _make_tiny_png()

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT TESTS
# ─────────────────────────────────────────────────────────────────────────────
print("=== ENDPOINT TEST RESULTS ===\n")

ticket_id = None

# ── TC-001  POST /api/v1/tickets ──────────────────────────────────────────────
r = client.post("/api/v1/tickets",
                json={"title": "My laptop is not connecting to WiFi"})
if r.status_code == 201:
    body = r.json()
    tc001_ok = (
        isinstance(body.get("id"), int)
        and str(body.get("ticket_id", "")).startswith("TKT-")
        and body.get("status") == "Open"
    )
    ticket_id = body.get("id") if tc001_ok else None
    record("TC-001  POST /tickets", tc001_ok, 201,
           f"id={body.get('id')} ticket_id={body.get('ticket_id')} status={body.get('status')}"
           if tc001_ok else f"unexpected body: {body}")
else:
    record("TC-001  POST /tickets", False, r.status_code, r.text[:300])

# ── TC-003  POST /api/v1/tickets/{id}/screenshots ─────────────────────────────
if ticket_id:
    r = client.post(
        f"/api/v1/tickets/{ticket_id}/screenshots",
        files={"file": ("pixel.png", io.BytesIO(TINY_PNG), "image/png")},
    )
    if r.status_code == 200:
        body = r.json()
        tc003_ok = "screenshot_path" in body
        record("TC-003  POST /tickets/{id}/screenshots", tc003_ok, 200,
               body.get("screenshot_path", "") if tc003_ok
               else f"missing screenshot_path: {body}")
    else:
        record("TC-003  POST /tickets/{id}/screenshots", False, r.status_code, r.text[:200])
else:
    record("TC-003  POST /tickets/{id}/screenshots", False, "N/A",
           "Skipped — TC-001 failed")

# ── TC-006  POST /api/v1/tickets/{id}/messages ───────────────────────────────
if ticket_id:
    r = client.post(f"/api/v1/tickets/{ticket_id}/messages",
                    json={"content": "My wifi keeps dropping"})
    if r.status_code == 200:
        body = r.json()
        tc006_ok = (
            "user_message" in body
            and "assistant_message" in body
            and isinstance(body.get("screenshot_requested"), bool)
            and isinstance(body.get("escalation_recommended"), bool)
        )
        record("TC-006  POST /tickets/{id}/messages", tc006_ok, 200,
               (f"user_msg_id={body['user_message']['id']} "
                f"asst_msg_id={body['assistant_message']['id']} "
                f"screenshot_req={body['screenshot_requested']} "
                f"escalation_rec={body['escalation_recommended']}")
               if tc006_ok else f"missing keys or wrong types: {body}")
    else:
        record("TC-006  POST /tickets/{id}/messages", False, r.status_code,
               r.text[:300])
else:
    record("TC-006  POST /tickets/{id}/messages", False, "N/A", "Skipped")

# ── TC-007  POST /api/v1/tickets/{id}/resolve ────────────────────────────────
r_new = client.post("/api/v1/tickets", json={"title": "Resolve test ticket"})
resolve_id = r_new.json().get("id") if r_new.status_code == 201 else ticket_id

if resolve_id:
    r = client.post(f"/api/v1/tickets/{resolve_id}/resolve")
    if r.status_code == 200:
        body = r.json()
        tc007_ok = body.get("status") == "Resolved"
        record("TC-007  POST /tickets/{id}/resolve", tc007_ok, 200,
               f"status={body.get('status')}" if tc007_ok
               else f"wrong status: {body}")
    else:
        record("TC-007  POST /tickets/{id}/resolve", False, r.status_code, r.text[:200])
else:
    record("TC-007  POST /tickets/{id}/resolve", False, "N/A", "Skipped")

# ── TC-008  POST /api/v1/tickets/{id}/escalate ───────────────────────────────
r_esc = client.post("/api/v1/tickets", json={"title": "Escalate test ticket"})
escalate_id = r_esc.json().get("id") if r_esc.status_code == 201 else None

if escalate_id:
    r = client.post(f"/api/v1/tickets/{escalate_id}/escalate")
    if r.status_code == 200:
        body = r.json()
        tc008e_ok = body.get("status") == "Escalated"
        record("TC-008  POST /tickets/{id}/escalate", tc008e_ok, 200,
               f"status={body.get('status')}" if tc008e_ok
               else f"wrong status: {body}")
    else:
        record("TC-008  POST /tickets/{id}/escalate", False, r.status_code, r.text[:200])
else:
    record("TC-008  POST /tickets/{id}/escalate", False, "N/A", "Skipped")

# ── TC-008  POST /api/v1/tickets/{id}/satisfaction ───────────────────────────
if ticket_id:
    r = client.post(f"/api/v1/tickets/{ticket_id}/satisfaction",
                    json={"rating": 1})
    if r.status_code == 200:
        body = r.json()
        tc008s_ok = body.get("satisfaction") == 1
        record("        POST /tickets/{id}/satisfaction", tc008s_ok, 200,
               f"satisfaction={body.get('satisfaction')}" if tc008s_ok
               else f"wrong value: {body}")
    else:
        record("        POST /tickets/{id}/satisfaction", False, r.status_code,
               r.text[:200])
else:
    record("        POST /tickets/{id}/satisfaction", False, "N/A", "Skipped")

# ── TC-009  GET /api/v1/solutions/search?q=wifi ──────────────────────────────
r = client.get("/api/v1/solutions/search?q=wifi")
if r.status_code == 200:
    data = r.json()
    tc009_ok = isinstance(data, list)
    record("TC-009  GET  /solutions/search", tc009_ok, 200,
           f"returned {len(data)} results" if tc009_ok
           else f"not a list: {type(data)}")
else:
    record("TC-009  GET  /solutions/search", False, r.status_code, r.text[:200])

# ── TC-013  GET /api/v1/analytics/summary ────────────────────────────────────
r = client.get("/api/v1/analytics/summary")
if r.status_code == 200:
    body = r.json()
    REQUIRED_FIELDS = {
        "total_tickets","open_tickets","resolved_tickets","escalated_tickets",
        "ai_resolution_rate","avg_failed_attempts","today_tickets",
        "week_tickets","month_tickets",
    }
    missing = REQUIRED_FIELDS - set(body.keys()) if isinstance(body, dict) else REQUIRED_FIELDS
    tc013s_ok = not missing
    record("TC-013  GET  /analytics/summary", tc013s_ok, 200,
           "all required fields present" if tc013s_ok
           else f"missing fields: {missing}")
else:
    record("TC-013  GET  /analytics/summary", False, r.status_code, r.text[:200])

# ── TC-013  GET /api/v1/analytics/common-issues ──────────────────────────────
r = client.get("/api/v1/analytics/common-issues")
if r.status_code == 200:
    data = r.json()
    tc013ci_ok = isinstance(data, list)
    record("TC-013  GET  /analytics/common-issues", tc013ci_ok, 200,
           f"returned {len(data)} rows" if tc013ci_ok
           else f"not a list: {type(data)}")
else:
    record("TC-013  GET  /analytics/common-issues", False, r.status_code, r.text[:200])

# ── GET /api/v1/tickets (list) ────────────────────────────────────────────────
r = client.get("/api/v1/tickets")
if r.status_code == 200:
    data = r.json()
    list_ok = isinstance(data, list)
    record("        GET  /tickets", list_ok, 200,
           f"returned {len(data)} tickets" if list_ok
           else f"not a list: {type(data)}")
else:
    record("        GET  /tickets", False, r.status_code, r.text[:200])

# ── GET /api/v1/tickets/{id} (with messages) ─────────────────────────────────
if ticket_id:
    r = client.get(f"/api/v1/tickets/{ticket_id}")
    if r.status_code == 200:
        body = r.json()
        get_ok = "messages" in body
        record("        GET  /tickets/{id}", get_ok, 200,
               f"messages count={len(body.get('messages',[]))}" if get_ok
               else f"no 'messages' key: {list(body.keys())}")
    else:
        record("        GET  /tickets/{id}", False, r.status_code, r.text[:200])
else:
    record("        GET  /tickets/{id}", False, "N/A", "Skipped")

# ── PATCH /api/v1/tickets/{id} ───────────────────────────────────────────────
if ticket_id:
    r = client.patch(f"/api/v1/tickets/{ticket_id}", json={"severity": "High"})
    if r.status_code == 200:
        body = r.json()
        patch_ok = body.get("severity") == "High"
        record("        PATCH /tickets/{id}", patch_ok, 200,
               f"severity={body.get('severity')}" if patch_ok
               else f"wrong severity: {body}")
    else:
        record("        PATCH /tickets/{id}", False, r.status_code, r.text[:200])
else:
    record("        PATCH /tickets/{id}", False, "N/A", "Skipped")

print()

# ─────────────────────────────────────────────────────────────────────────────
# BUG CHECKS
# ─────────────────────────────────────────────────────────────────────────────
print("=== BUG CHECKS ===\n")

import services.claude as _claude_mod

# ── B-001  Malformed category_data — must not 500 ────────────────────────────
r_b1 = client.post("/api/v1/tickets", json={"title": "B001 malformed cat test"})
b001_tid = r_b1.json().get("id") if r_b1.status_code == 201 else None

if b001_tid:
    malformed = dict(FAKE_RESULT, category_data="NOT A DICT — intentionally broken")
    _orig_fn = _claude_mod.process_chat_turn
    _claude_mod.process_chat_turn = lambda h, f: malformed
    try:
        r = client.post(f"/api/v1/tickets/{b001_tid}/messages",
                        json={"content": "Testing malformed category_data"})
    finally:
        _claude_mod.process_chat_turn = _orig_fn

    b001_ok = r.status_code != 500
    record("BUG B-001 (JSON parse crash)", b001_ok, r.status_code,
           "Handled gracefully — no 500" if b001_ok
           else f"SERVER CRASHED 500: {r.text[:200]}")
else:
    record("BUG B-001 (JSON parse crash)", False, "N/A",
           "Could not create test ticket")

# ── B-002  "still not working" increments failed_attempts ────────────────────
r_b2 = client.post("/api/v1/tickets", json={"title": "B002 failed_attempts test"})
b002_tid = r_b2.json().get("id") if r_b2.status_code == 201 else None

if b002_tid:
    before = client.get(f"/api/v1/tickets/{b002_tid}").json().get("failed_attempts", -1)
    r = client.post(f"/api/v1/tickets/{b002_tid}/messages",
                    json={"content": "still not working"})
    if r.status_code == 200:
        after = client.get(f"/api/v1/tickets/{b002_tid}").json().get("failed_attempts", -1)
        b002_ok = after == before + 1
        record("BUG B-002 (failed_attempts persists)", b002_ok, "",
               f"before={before} after={after}"
               + ("" if b002_ok else " — DID NOT INCREMENT"))
    else:
        record("BUG B-002 (failed_attempts persists)", False, r.status_code,
               f"Message endpoint failed: {r.text[:200]}")
else:
    record("BUG B-002 (failed_attempts persists)", False, "N/A",
           "Could not create ticket")

# ── B-007  resolved_at is set after /resolve ─────────────────────────────────
r_b7 = client.post("/api/v1/tickets", json={"title": "B007 resolved_at test"})
b007_tid = r_b7.json().get("id") if r_b7.status_code == 201 else None

if b007_tid:
    client.post(f"/api/v1/tickets/{b007_tid}/resolve")
    body = client.get(f"/api/v1/tickets/{b007_tid}").json()
    b007_ok = body.get("resolved_at") is not None
    record("BUG B-007 (resolved_at set)", b007_ok, "",
           f"resolved_at={body.get('resolved_at')}" if b007_ok
           else "resolved_at is NULL after /resolve!")
else:
    record("BUG B-007 (resolved_at set)", False, "N/A",
           "Could not create ticket")

# ── B-008  CORS allows http://localhost:5173 ──────────────────────────────────
import config as _cfg
_cfg.get_settings.cache_clear()
_cors_setting = _cfg.get_settings().cors_allowed_origins
cors_origins = [o.strip() for o in _cors_setting.split(",")]
b008_ok = "http://localhost:5173" in cors_origins
record("BUG B-008 (CORS configured)", b008_ok, "",
       f"origins={cors_origins}" if b008_ok
       else f"localhost:5173 NOT found in CORS origins: {cors_origins}")

# ─────────────────────────────────────────────────────────────────────────────
# FINAL REPORT
# ─────────────────────────────────────────────────────────────────────────────
print()
print("=" * 80)
print()

print("=== STATIC ANALYSIS ===")
if static_bugs:
    for tag, msg in static_bugs:
        print(f"  [{tag}] {msg}")
else:
    print("  (no bugs found)")

print()
print("=== IMPORT TEST ===")
if not import_errors:
    print("  PASS — all 14 modules imported successfully")
else:
    for mod, err in import_errors.items():
        print(f"  FAIL — {mod}: {err}")

print()
print("=== ENDPOINT TEST RESULTS ===")

ENDPOINT_LABELS = [
    "TC-001  POST /tickets",
    "TC-003  POST /tickets/{id}/screenshots",
    "TC-006  POST /tickets/{id}/messages",
    "TC-007  POST /tickets/{id}/resolve",
    "TC-008  POST /tickets/{id}/escalate",
    "        POST /tickets/{id}/satisfaction",
    "TC-009  GET  /solutions/search",
    "TC-013  GET  /analytics/summary",
    "TC-013  GET  /analytics/common-issues",
    "        GET  /tickets",
    "        GET  /tickets/{id}",
    "        PATCH /tickets/{id}",
]
BUG_LABELS = [
    "BUG B-001 (JSON parse crash)",
    "BUG B-002 (failed_attempts persists)",
    "BUG B-007 (resolved_at set)",
    "BUG B-008 (CORS configured)",
]

result_map = {r[0]: r for r in RESULTS}

for lbl in ENDPOINT_LABELS:
    if lbl in result_map:
        _, passed, code, notes = result_map[lbl]
        status = "PASS" if passed else "FAIL"
        code_col = f"[{code}]" if code and code not in ("N/A","") else "     "
        print(f"  {lbl:<46} [{status}] {code_col:<6} {notes}")

print()
for lbl in BUG_LABELS:
    if lbl in result_map:
        _, passed, code, notes = result_map[lbl]
        status = "PASS" if passed else "FAIL"
        print(f"  {lbl:<46} [{status}] {notes}")

print()
total_pass = sum(1 for r in RESULTS if r[1])
total_fail = sum(1 for r in RESULTS if not r[1])
print("=== SUMMARY ===")
print(f"Total: {total_pass} passed, {total_fail} failed")
print()

print("Root cause of original 500 error:")
root_msgs = [msg for tag, msg in static_bugs if tag in ("SA-1","SA-4")]
if root_msgs:
    for m in root_msgs:
        print(f"  - {m}")
else:
    print("  Not detected in static analysis (all imports passed).")

print()
print("Other bugs found:")
failed_items = [(lbl, notes) for (lbl, passed, _, notes) in RESULTS if not passed]
if failed_items:
    for lbl, notes in failed_items:
        print(f"  - {lbl}: {notes}")
else:
    print("  None")

print()
print("Static analysis notes and bugs:")
if static_bugs:
    for tag, msg in static_bugs:
        print(f"  [{tag}] {msg}")
else:
    print("  None")

# ── Cleanup temp DB ───────────────────────────────────────────────────────────
try:
    if _db_file.exists():
        _db_file.unlink()
except Exception:
    pass   # Windows lock — leave it; it's in /tmp
