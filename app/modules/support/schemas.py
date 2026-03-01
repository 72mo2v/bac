from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from app.modules.support.models import TicketStatus, TicketPriority, TicketCategory

# User minimal schema for ticket responses
class UserMinimal(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: str
    
    class Config:
        from_attributes = True

# Ticket Message Schemas
class TicketMessageBase(BaseModel):
    message: str
    is_internal: int = 0

class TicketMessageCreate(TicketMessageBase):
    pass

class TicketMessage(TicketMessageBase):
    id: int
    ticket_id: int
    user_id: int
    author: Optional[UserMinimal] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Support Ticket Schemas
class SupportTicketBase(BaseModel):
    subject: str
    category: TicketCategory = TicketCategory.OTHER
    priority: TicketPriority = TicketPriority.MEDIUM

class SupportTicketCreate(SupportTicketBase):
    message: str  # First message content

class SupportTicketUpdate(BaseModel):
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    assigned_to: Optional[int] = None

class SupportTicket(SupportTicketBase):
    id: int
    ticket_number: str
    customer_id: int
    assigned_to: Optional[int] = None
    status: TicketStatus
    customer: Optional[UserMinimal] = None
    assigned_agent: Optional[UserMinimal] = None
    messages: List[TicketMessage] = []
    created_at: datetime
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class SupportTicketList(BaseModel):
    id: int
    ticket_number: str
    subject: str
    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus
    customer: Optional[UserMinimal] = None
    assigned_agent: Optional[UserMinimal] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
