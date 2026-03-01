from typing import List, Optional
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import joinedload, selectinload
from app.core.base_repository import BaseRepository
from app.modules.support.models import SupportTicket, TicketMessage, TicketStatus

class SupportTicketRepository(BaseRepository[SupportTicket]):
    def __init__(self, db):
        super().__init__(SupportTicket, db)

    async def get_with_messages(self, ticket_id: int) -> Optional[SupportTicket]:
        """Get ticket with all messages and related data"""
        query = select(SupportTicket).options(
            joinedload(SupportTicket.customer),
            joinedload(SupportTicket.assigned_agent),
            selectinload(SupportTicket.messages).selectinload(TicketMessage.author)
        ).filter(SupportTicket.id == ticket_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_customer_tickets(
        self, 
        customer_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[SupportTicket]:
        """Get all tickets for a specific customer with archiving logic"""
        from datetime import datetime, timedelta
        one_day_ago = datetime.now() - timedelta(days=1)
        
        query = select(SupportTicket).options(
            joinedload(SupportTicket.customer),
            joinedload(SupportTicket.assigned_agent)
        ).filter(
            SupportTicket.customer_id == customer_id
        ).filter(
            or_(
                SupportTicket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.WAITING_CUSTOMER]),
                and_(
                    SupportTicket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
                    or_(
                        SupportTicket.resolved_at >= one_day_ago,
                        SupportTicket.closed_at >= one_day_ago,
                        and_(SupportTicket.resolved_at == None, SupportTicket.closed_at == None, SupportTicket.updated_at >= one_day_ago)
                    )
                )
            )
        ).order_by(
            SupportTicket.created_at.asc()
        ).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_all_tickets(
        self,
        status: Optional[TicketStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[SupportTicket]:
        """Get all tickets with optional status filter (for admin)"""
        from datetime import datetime, timedelta
        
        query = select(SupportTicket).options(
            joinedload(SupportTicket.customer),
            joinedload(SupportTicket.assigned_agent)
        )
        
        if status:
            query = query.filter(SupportTicket.status == status)
        else:
            # Default view: Show all EXCEPT old resolved/closed tickets
            one_day_ago = datetime.now() - timedelta(days=1)
            query = query.filter(
                or_(
                    SupportTicket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.WAITING_CUSTOMER]),
                    and_(
                        SupportTicket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
                        or_(
                            SupportTicket.resolved_at >= one_day_ago,
                            SupportTicket.closed_at >= one_day_ago,
                            and_(SupportTicket.resolved_at == None, SupportTicket.closed_at == None, SupportTicket.updated_at >= one_day_ago)
                        )
                    )
                )
            )
        
        # Order by oldest first as requested
        query = query.order_by(SupportTicket.created_at.asc()).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_ticket_number(self, ticket_number: str) -> Optional[SupportTicket]:
        """Get ticket by ticket number"""
        query = select(SupportTicket).options(
            joinedload(SupportTicket.customer),
            joinedload(SupportTicket.assigned_agent),
            selectinload(SupportTicket.messages).selectinload(TicketMessage.author)
        ).filter(SupportTicket.ticket_number == ticket_number)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

class TicketMessageRepository(BaseRepository[TicketMessage]):
    def __init__(self, db):
        super().__init__(TicketMessage, db)
