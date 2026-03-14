from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    title        = Column(String(255), nullable=False, default="Untitled Ticket")
    category     = Column(String(50),  default="Other")
    severity     = Column(String(50),  default="Medium")
    priority     = Column(String(10),  default="P3")
    status       = Column(String(50),  default="Open")
    user_id      = Column(String(100), nullable=False, default="user")
    assigned_to  = Column(String(100), nullable=True)
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at  = Column(DateTime, nullable=True)
    solution     = Column(Text, nullable=True)
    satisfaction = Column(Integer, nullable=True)
    failed_attempts = Column(Integer, default=0)

    messages = relationship(
        "Message",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    @property
    def ticket_id(self) -> str:
        return f"TKT-{self.id:04d}"
