from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, timedelta

from database import get_db
from models.ticket import Ticket
from schemas import AnalyticsSummary, CommonIssue

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def get_summary(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    today_start  = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start   = today_start - timedelta(days=7)
    month_start  = today_start - timedelta(days=30)

    total     = db.query(func.count(Ticket.id)).scalar() or 0
    open_c    = db.query(func.count(Ticket.id)).filter(Ticket.status == "Open").scalar() or 0
    resolved  = db.query(func.count(Ticket.id)).filter(Ticket.status == "Resolved").scalar() or 0
    escalated = db.query(func.count(Ticket.id)).filter(Ticket.status == "Escalated").scalar() or 0
    today     = db.query(func.count(Ticket.id)).filter(Ticket.created_at >= today_start).scalar() or 0
    week      = db.query(func.count(Ticket.id)).filter(Ticket.created_at >= week_start).scalar() or 0
    month     = db.query(func.count(Ticket.id)).filter(Ticket.created_at >= month_start).scalar() or 0

    avg_result = db.query(func.avg(Ticket.failed_attempts)).scalar()
    avg_attempts = float(avg_result) if avg_result is not None else 0.0

    return AnalyticsSummary(
        total_tickets=total,
        open_tickets=open_c,
        resolved_tickets=resolved,
        escalated_tickets=escalated,
        ai_resolution_rate=round(resolved / total, 4) if total > 0 else 0.0,
        avg_failed_attempts=round(avg_attempts, 2),
        today_tickets=today,
        week_tickets=week,
        month_tickets=month,
    )


@router.get("/common-issues", response_model=list[CommonIssue])
def get_common_issues(db: Session = Depends(get_db)):
    rows = (
        db.query(Ticket.category, func.count(Ticket.id).label("cnt"))
        .group_by(Ticket.category)
        .order_by(func.count(Ticket.id).desc())
        .limit(10)
        .all()
    )
    results = []
    for row in rows:
        resolved_count = (
            db.query(func.count(Ticket.id))
            .filter(Ticket.category == row.category, Ticket.status == "Resolved")
            .scalar() or 0
        )
        results.append(CommonIssue(
            category=row.category,
            count=row.cnt,
            resolution_rate=round(resolved_count / row.cnt, 4) if row.cnt > 0 else 0.0,
        ))
    return results
