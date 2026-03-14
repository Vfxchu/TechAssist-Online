import re
import shutil
import time
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from database import get_db
from models.ticket import Ticket
from models.message import Message
from schemas import SendMessageRequest, SendMessageResponse, MessageOut, TicketOut
from services.claude import process_chat_turn
from services.solutions import save_solution, find_matching_solution
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/tickets", tags=["messages"])
limiter = Limiter(key_func=get_remote_address)

# Phrases that indicate the last suggestion did not work
_NEGATIVE_PHRASES = (
    "didn't work", "didnt work", "still not working", "not working",
    "doesn't work", "doesnt work", "still broken", "no luck",
    "failed", "same issue", "same problem", "not fixed", "still happening",
)


@router.post("/{ticket_id}/messages", response_model=SendMessageResponse)
@limiter.limit("20/minute")
def send_message(
    request: Request,
    ticket_id: int,
    req: SendMessageRequest,
    db: Session = Depends(get_db),
):
    ticket = _get_open_ticket(ticket_id, db)

    # Detect negative response (will increment after AI responds successfully)
    is_negative = any(p in req.content.lower() for p in _NEGATIVE_PHRASES)

    # Persist user message
    user_msg = Message(
        ticket_id=ticket_id,
        role="user",
        content=req.content,
        screenshot_path=req.screenshot_path,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Build conversation history for Claude (all messages in order)
    all_msgs = (
        db.query(Message)
        .filter(Message.ticket_id == ticket_id)
        .order_by(Message.created_at)
        .all()
    )
    claude_history = []
    for m in all_msgs:
        text = m.content
        if m.screenshot_path:
            text += f"\n[User attached screenshot: {m.screenshot_path}]"
        claude_history.append({"role": m.role, "content": text})

    # Check solution memory on first user message (before calling Claude)
    solution_context = ""
    if len(all_msgs) == 1:  # only the user message we just added
        all_text = req.content
        matched = find_matching_solution(
            db=db,
            category=ticket.category or "Other",
            os_name=_extract_os(all_text),
            software=_extract_software(all_text),
            issue_keywords=all_text.lower().split(),
        )
        if matched:
            solution_context = (
                f"\n\n[SOLUTION MEMORY: A similar past issue was resolved with: "
                f"{matched.solution_steps[:500]}]"
            )
            claude_history[0]["content"] += solution_context

    # Call Claude
    result = process_chat_turn(claude_history, ticket.failed_attempts)

    # Increment failed_attempts only after a successful AI response
    if is_negative:
        ticket.failed_attempts += 1

    # Apply silent category/severity update (Phase 2)
    cat = result.get("category_data")
    if cat:
        if ticket.category in ("Other", None):
            ticket.category = cat.get("category", ticket.category)
        if ticket.severity in ("Medium", None):
            ticket.severity = cat.get("severity", ticket.severity)
        if cat.get("suggested_title") and ticket.title == "Untitled Ticket":
            ticket.title = cat["suggested_title"][:255]

    # Handle Phase 4 status actions
    action = result.get("action_needed")
    if action == "resolved":
        ticket.status = "Resolved"
        ticket.resolved_at = datetime.now(timezone.utc)
        # Persist to solution memory
        all_text = " ".join(m.content for m in all_msgs)
        save_solution(
            db=db,
            category=ticket.category or "Other",
            os_name=_extract_os(all_text),
            software=_extract_software(all_text),
            issue_summary=ticket.title,
            solution_steps=result["content"][:2000],
            source_ticket_id=ticket.ticket_id,
        )
    elif action == "escalate":
        ticket.status = "Escalated"

    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()

    # Persist assistant message
    ai_msg = Message(
        ticket_id=ticket_id,
        role="assistant",
        content=result["content"],
    )
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)

    return SendMessageResponse(
        user_message=_msg_out(user_msg),
        assistant_message=_msg_out(ai_msg),
        screenshot_requested=result["screenshot_requested"],
        escalation_recommended=result["escalation_recommended"],
        action_needed=action,
        ticket=_ticket_out(ticket),
    )


def _ticket_out(ticket: Ticket) -> TicketOut:
    return TicketOut(
        id=ticket.id,
        ticket_id=ticket.ticket_id,
        title=ticket.title,
        status=ticket.status,
        category=ticket.category,
        severity=ticket.severity,
        priority=ticket.priority,
        user_id=ticket.user_id,
        assigned_to=ticket.assigned_to,
        failed_attempts=ticket.failed_attempts,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        satisfaction=ticket.satisfaction,
        solution=ticket.solution,
    )


@router.post("/{ticket_id}/screenshots")
async def upload_screenshot(
    ticket_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "upload.png").suffix or ".png"
    filename = f"ticket_{ticket_id}_{int(time.time())}{suffix}"
    filepath = upload_dir / filename

    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {"screenshot_path": f"/uploads/{filename}", "filename": filename}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_open_ticket(ticket_id: int, db: Session) -> Ticket:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.status in ("Resolved", "Closed", "Escalated"):
        raise HTTPException(status_code=400, detail="Ticket is not open")
    return ticket


def _msg_out(m: Message) -> MessageOut:
    return MessageOut(
        id=m.id,
        ticket_id=m.ticket_id,
        role=m.role,
        content=m.content,
        screenshot_path=m.screenshot_path,
        created_at=m.created_at,
    )


def _extract_os(text: str) -> str:
    patterns = [
        r"(Windows\s+\d+(?:\s+\w+)?)",
        r"(macOS\s+\w+(?:\s+\d+[\d.]*)?)",
        r"(Mac\s+OS\s+X)",
        r"(Ubuntu\s+[\d.]+)",
        r"(Debian\s+[\d.]+)",
        r"(Linux)",
        r"(iOS\s+[\d.]+)",
        r"(Android\s+[\d.]+)",
        r"(Chrome\s*OS)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return "Unknown"


def _extract_software(text: str) -> str:
    patterns = [
        r"(Microsoft\s+\w+)",
        r"(Chrome(?:\s+\d+)?)",
        r"(Firefox(?:\s+\d+)?)",
        r"(Outlook(?:\s+\d+)?)",
        r"(Microsoft\s+Teams)",
        r"(Teams)",
        r"(Excel)",
        r"(Word)",
        r"(PowerPoint)",
        r"(Zoom(?:\s+\d+)?)",
        r"(Slack)",
        r"(Visual\s+Studio(?:\s+Code)?)",
        r"(OneDrive)",
        r"(SharePoint)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return "Unknown"
