from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ---------------------------------------------------------------------------
# Ticket (Moved up to avoid NameError/Forward Refs)
# ---------------------------------------------------------------------------

class TicketCreate(BaseModel):
    title: str
    user_id: str = "user"


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    title: Optional[str] = None


class TicketOut(BaseModel):
    id: int
    ticket_id: str
    title: str
    category: str
    severity: str
    priority: str
    status: str
    user_id: str
    assigned_to: Optional[str]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    solution: Optional[str]
    satisfaction: Optional[int]
    failed_attempts: int

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

class MessageOut(BaseModel):
    id: int
    ticket_id: int
    role: str
    content: str
    screenshot_path: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    content: str
    screenshot_path: Optional[str] = None


class SendMessageResponse(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
    screenshot_requested: bool
    escalation_recommended: bool
    action_needed: Optional[str] = None   # "resolved" | "escalate" | None
    ticket: TicketOut


class TicketWithMessages(TicketOut):
    messages: List[MessageOut] = []


# ---------------------------------------------------------------------------
# Resolve / Escalate / Satisfaction
# ---------------------------------------------------------------------------

class ResolveRequest(BaseModel):
    solution: Optional[str] = None


class SatisfactionRequest(BaseModel):
    rating: int   # 1 or -1


# ---------------------------------------------------------------------------
# Solution memory
# ---------------------------------------------------------------------------

class SolutionOut(BaseModel):
    id: int
    category: str
    os: str
    software: str
    issue_summary: str
    solution_steps: str
    source_ticket_id: str
    success_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

class AnalyticsSummary(BaseModel):
    total_tickets: int
    open_tickets: int
    resolved_tickets: int
    escalated_tickets: int
    ai_resolution_rate: float
    avg_failed_attempts: float
    today_tickets: int
    week_tickets: int
    month_tickets: int


class CommonIssue(BaseModel):
    category: str
    count: int
    resolution_rate: float
