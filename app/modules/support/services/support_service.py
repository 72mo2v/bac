from typing import List, Optional
from datetime import datetime
from app.modules.support.repositories.support_repository import SupportTicketRepository, TicketMessageRepository
from app.modules.support.schemas import SupportTicketCreate, SupportTicketUpdate, TicketMessageCreate
from app.modules.support.models import SupportTicket, TicketMessage, TicketStatus
from app.modules.notifications.connection_manager import manager
from sqlalchemy import select
from sqlalchemy.orm import joinedload
import secrets

class SupportService:
    def __init__(self, ticket_repo: SupportTicketRepository, message_repo: TicketMessageRepository):
        self.ticket_repo = ticket_repo
        self.message_repo = message_repo

    def _generate_ticket_number(self) -> str:
        """Generate unique ticket number"""
        timestamp = datetime.now().strftime("%Y%m%d")
        random_part = secrets.token_hex(3).upper()
        return f"TKT-{timestamp}-{random_part}"

    async def create_ticket(self, ticket_data: SupportTicketCreate, customer_id: int) -> SupportTicket:
        """Create new support ticket with initial message"""
        # Generate unique ticket number
        ticket_number = self._generate_ticket_number()
        
        # Create ticket
        ticket_dict = ticket_data.model_dump(exclude={'message'})
        ticket_dict['ticket_number'] = ticket_number
        ticket_dict['customer_id'] = customer_id
        ticket_dict['status'] = TicketStatus.OPEN
        
        ticket = await self.ticket_repo.create(ticket_dict)
        
        # Create first message
        message_data = {
            'ticket_id': ticket.id,
            'user_id': customer_id,
            'message': ticket_data.message,
            'is_internal': 0
        }
        await self.message_repo.create(message_data)
        
        # Refresh to get messages
        return await self.ticket_repo.get_with_messages(ticket.id)

    async def add_message(self, ticket_id: int, message_data: TicketMessageCreate, user_id: int) -> TicketMessage:
        """Add message to existing ticket and notify recipient via WebSocket"""
        message_dict = message_data.model_dump()
        message_dict['ticket_id'] = ticket_id
        message_dict['user_id'] = user_id
        
        message = await self.message_repo.create(message_dict)
        
        # Fetch message with author details for the return and websocket
        query = select(TicketMessage).options(joinedload(TicketMessage.author)).filter(TicketMessage.id == message.id)
        res = await self.message_repo.db.execute(query)
        message_with_author = res.scalar_one()

        # Update ticket's updated_at
        ticket = await self.ticket_repo.get_with_messages(ticket_id)
        if ticket:
            await self.ticket_repo.update(ticket, {'updated_at': datetime.now()})
            
            # WebSocket Notification
            payload = {
                "type": "support_message",
                "ticket_id": ticket_id,
                "message": {
                    "id": message_with_author.id,
                    "message": message_with_author.message,
                    "user_id": message_with_author.user_id,
                    "created_at": message_with_author.created_at.isoformat(),
                    "author": {
                        "id": message_with_author.author.id,
                        "full_name": message_with_author.author.full_name,
                        "email": message_with_author.author.email
                    }
                }
            }
            
            # Notify the other party
            recipient_id = None
            if user_id == ticket.customer_id:
                # Customer sent message -> Notify assigned agent or all admins if not assigned
                recipient_id = ticket.assigned_to 
                # If no agent assigned, we could broadcast to admins, 
                # but for now let's try to notify the assigned agent if exists
            else:
                # Admin/Agent sent message -> Notify customer
                recipient_id = ticket.customer_id
            
            if recipient_id:
                await manager.send_personal_message(payload, recipient_id)
            else:
                # If no specific recipient (e.g. no agent assigned), broadcast to all connected? 
                # Maybe too broad. Let's at least broadcast to all connected for now if it's for admins
                if user_id == ticket.customer_id:
                    await manager.broadcast(payload) # Notify all admins of new activity
        
        return message_with_author

    async def update_ticket(self, ticket_id: int, update_data: SupportTicketUpdate) -> SupportTicket:
        """Update ticket status, priority, or assignment"""
        update_dict = update_data.model_dump(exclude_unset=True)
        
        # If status is being changed to resolved or closed, set timestamp
        if 'status' in update_dict:
            if update_dict['status'] == TicketStatus.RESOLVED and not update_dict.get('resolved_at'):
                update_dict['resolved_at'] = datetime.now()
            elif update_dict['status'] == TicketStatus.CLOSED and not update_dict.get('closed_at'):
                update_dict['closed_at'] = datetime.now()
        
        ticket = await self.ticket_repo.get(ticket_id)
        if not ticket:
            raise ValueError("Ticket not found")
            
        await self.ticket_repo.update(ticket, update_dict)
        return await self.ticket_repo.get_with_messages(ticket_id)

    async def get_customer_tickets(self, customer_id: int, skip: int = 0, limit: int = 50) -> List[SupportTicket]:
        """Get all tickets for a customer"""
        return await self.ticket_repo.get_customer_tickets(customer_id, skip, limit)

    async def get_all_tickets(self, status: Optional[TicketStatus] = None, skip: int = 0, limit: int = 100) -> List[SupportTicket]:
        """Get all tickets (admin only)"""
        return await self.ticket_repo.get_all_tickets(status, skip, limit)

    async def get_ticket_by_id(self, ticket_id: int) -> Optional[SupportTicket]:
        """Get ticket with messages"""
        return await self.ticket_repo.get_with_messages(ticket_id)

    async def get_ticket_by_number(self, ticket_number: str) -> Optional[SupportTicket]:
        """Get ticket by ticket number"""
        return await self.ticket_repo.get_by_ticket_number(ticket_number)
