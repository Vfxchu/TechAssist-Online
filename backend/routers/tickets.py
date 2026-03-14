from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from database import get_db
from models.ticket import Ticket
from models.message import Message
from schemas import (
    TicketCreate, TicketUpdate, TicketOut, TicketWithMessages,
    MessageOut, SatisfactionRequest,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ticket_out(ticket: Ticket) -> TicketOut:
    return TicketOut(
        id=ticket.id,
        ticket_id=ticket.ticket_id,
        title=ticket.title,
        category=ticket.category,
        severity=ticket.severity,
        priority=ticket.priority,
        status=ticket.status,
        user_id=ticket.user_id,
        assigned_to=ticket.assigned_to,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        solution=ticket.solution,
        satisfaction=ticket.satisfaction,
        failed_attempts=ticket.failed_attempts,
    )


def _ticket_with_messages(ticket: Ticket) -> TicketWithMessages:
    messages = [
        MessageOut(
            id=m.id,
            ticket_id=m.ticket_id,
            role=m.role,
            content=m.content,
            screenshot_path=m.screenshot_path,
            created_at=m.created_at,
        )
        for m in ticket.messages
    ]
    return TicketWithMessages(**_ticket_out(ticket).model_dump(), messages=messages)


def _get_or_404(ticket_id: int, db: Session) -> Ticket:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=TicketOut, status_code=201)
def create_ticket(req: TicketCreate, db: Session = Depends(get_db)):
    ticket = Ticket(title=req.title[:255], user_id=req.user_id)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return _ticket_out(ticket)


@router.get("", response_model=list[TicketOut])
def list_tickets(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(Ticket)
    if status:
        q = q.filter(Ticket.status == status)
    tickets = q.order_by(Ticket.updated_at.desc()).offset(offset).limit(limit).all()
    return [_ticket_out(t) for t in tickets]


@router.get("/{ticket_id}", response_model=TicketWithMessages)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = _get_or_404(ticket_id, db)
    return _ticket_with_messages(ticket)


@router.patch("/{ticket_id}", response_model=TicketOut)
def update_ticket(ticket_id: int, req: TicketUpdate, db: Session = Depends(get_db)):
    ticket = _get_or_404(ticket_id, db)
    for field, value in req.model_dump(exclude_none=True).items():
        setattr(ticket, field, value)
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    return _ticket_out(ticket)


@router.post("/{ticket_id}/resolve", response_model=TicketOut)
def resolve_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = _get_or_404(ticket_id, db)
    ticket.status = "Resolved"
    ticket.resolved_at = datetime.now(timezone.utc)
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    return _ticket_out(ticket)


@router.post("/{ticket_id}/escalate", response_model=TicketOut)
def escalate_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = _get_or_404(ticket_id, db)
    ticket.status = "Escalated"
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    return _ticket_out(ticket)


@router.post("/{ticket_id}/satisfaction", response_model=TicketOut)
def submit_satisfaction(
    ticket_id: int, req: SatisfactionRequest, db: Session = Depends(get_db)
):
    if req.rating not in (1, -1):
        raise HTTPException(status_code=400, detail="Rating must be 1 or -1")
    ticket = _get_or_404(ticket_id, db)
    ticket.satisfaction = req.rating
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    return _ticket_out(ticket)
