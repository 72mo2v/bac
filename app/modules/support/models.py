from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base

class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"

class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TicketCategory(str, enum.Enum):
    TECHNICAL = "technical"
    BILLING = "billing"
    PRODUCT = "product"
    SHIPPING = "shipping"
    ACCOUNT = "account"
    OTHER = "other"

class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String, unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    
    subject = Column(String, nullable=False)
    category = Column(Enum(TicketCategory), default=TicketCategory.OTHER)
    priority = Column(Enum(TicketPriority), default=TicketPriority.MEDIUM)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    customer = relationship("app.modules.auth.models.User", foreign_keys=[customer_id])
    assigned_agent = relationship("app.modules.auth.models.User", foreign_keys=[assigned_to])
    messages = relationship("TicketMessage", back_populates="ticket", cascade="all, delete-orphan", order_by="TicketMessage.created_at")

class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    message = Column(Text, nullable=False)
    is_internal = Column(Integer, default=0)  # 0 = customer visible, 1 = internal note
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    ticket = relationship("SupportTicket", back_populates="messages")
    author = relationship("app.modules.auth.models.User")
