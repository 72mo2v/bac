from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.modules.auth.models import User, UserRole
from app.modules.support.schemas import (
    SupportTicket, SupportTicketCreate, SupportTicketUpdate, SupportTicketList,
    TicketMessage, TicketMessageCreate
)
from app.modules.support.models import TicketStatus
from app.modules.support.repositories.support_repository import SupportTicketRepository, TicketMessageRepository
from app.modules.support.services.support_service import SupportService

router = APIRouter()

# Dependency
async def get_support_service(db: AsyncSession = Depends(get_db)) -> SupportService:
    ticket_repo = SupportTicketRepository(db)
    message_repo = TicketMessageRepository(db)
    return SupportService(ticket_repo, message_repo)

# Customer Endpoints
@router.post("/tickets", response_model=SupportTicket)
async def create_ticket(
    ticket_data: SupportTicketCreate,
    current_user: User = Depends(get_current_active_user),
    service: SupportService = Depends(get_support_service)
):
    """Create a new support ticket"""
    return await service.create_ticket(ticket_data, current_user.id)

@router.get("/tickets", response_model=List[SupportTicketList])
async def get_my_tickets(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    service: SupportService = Depends(get_support_service)
):
    """Get all tickets for current user"""
    return await service.get_customer_tickets(current_user.id, skip, limit)

@router.get("/tickets/{ticket_id}", response_model=SupportTicket)
async def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_active_user),
    service: SupportService = Depends(get_support_service)
):
    """Get ticket details with messages"""
    ticket = await service.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Check if user owns the ticket or is admin
    if ticket.customer_id != current_user.id and current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized to view this ticket")
    
    return ticket

@router.post("/tickets/{ticket_id}/messages", response_model=TicketMessage)
async def add_message_to_ticket(
    ticket_id: int,
    message_data: TicketMessageCreate,
    current_user: User = Depends(get_current_active_user),
    service: SupportService = Depends(get_support_service)
):
    """Add a message to a ticket"""
    ticket = await service.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Check if user owns the ticket or is admin
    if ticket.customer_id != current_user.id and current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized to add messages to this ticket")
    
    return await service.add_message(ticket_id, message_data, current_user.id)

# Admin Endpoints
@router.get("/admin/tickets", response_model=List[SupportTicketList])
async def get_all_tickets_admin(
    status: Optional[TicketStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    service: SupportService = Depends(get_support_service)
):
    """Get all tickets (admin only)"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return await service.get_all_tickets(status, skip, limit)

@router.patch("/admin/tickets/{ticket_id}", response_model=SupportTicket)
async def update_ticket_admin(
    ticket_id: int,
    update_data: SupportTicketUpdate,
    current_user: User = Depends(get_current_active_user),
    service: SupportService = Depends(get_support_service)
):
    """Update ticket status, priority, or assignment (admin only)"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    ticket = await service.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return await service.update_ticket(ticket_id, update_data)
