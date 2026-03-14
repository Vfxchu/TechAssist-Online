from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime, timezone
from database import Base


class Solution(Base):
    __tablename__ = "solutions"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    category         = Column(String(50),  nullable=False)
    os               = Column(String(100), nullable=False)
    software         = Column(String(100), nullable=False)
    issue_summary    = Column(Text, nullable=False)
    solution_steps   = Column(Text, nullable=False)
    source_ticket_id = Column(String(20), nullable=False)
    success_count    = Column(Integer, default=1)
    created_at       = Column(DateTime, default=lambda: datetime.now(timezone.utc))
