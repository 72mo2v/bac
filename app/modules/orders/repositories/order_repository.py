from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from app.core.base_repository import BaseRepository
from app.modules.orders.models import Order, OrderHistory, OrderItem, ReturnRequest, ReturnProofImage
from app.core.middleware import get_store_id
from app.modules.auth.models import User as UserModel

class OrderRepository(BaseRepository[Order]):
    def __init__(self, db):
        super().__init__(Order, db)

    async def get_with_items(self, id: int) -> Optional[Order]:
        query = select(Order).options(
            selectinload(Order.items).joinedload(OrderItem.product),
            selectinload(Order.history),
            selectinload(Order.store),
            selectinload(Order.customer),
        ).filter(Order.id == id)
        
        store_id = get_store_id()
        if store_id:
            query = query.filter(Order.store_id == store_id)
            
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_multi(self, skip: int = 0, limit: int = 100) -> List[Order]:
        query = select(Order).options(
            selectinload(Order.items).joinedload(OrderItem.product),
            selectinload(Order.store),
            selectinload(Order.customer),
        ).offset(skip).limit(limit).order_by(Order.created_at.desc())
        
        store_id = get_store_id()
        if store_id:
            query = query.filter(Order.store_id == store_id)
            
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_multi_by_customer(self, customer_id: int) -> List[Order]:
        query = select(Order).options(
            selectinload(Order.items).joinedload(OrderItem.product),
            selectinload(Order.store),
            selectinload(Order.customer),
        ).filter(Order.customer_id == customer_id).order_by(Order.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

class OrderHistoryRepository(BaseRepository[OrderHistory]):
    def __init__(self, db):
        super().__init__(OrderHistory, db)


class ReturnRequestRepository(BaseRepository[ReturnRequest]):
    def __init__(self, db):
        super().__init__(ReturnRequest, db)

    async def get_with_images(self, id: int) -> Optional[ReturnRequest]:
        query = select(ReturnRequest).options(
            selectinload(ReturnRequest.proof_images)
        ).filter(ReturnRequest.id == id)

        store_id = get_store_id()
        if store_id:
            query = query.filter(ReturnRequest.store_id == store_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()


class ReturnProofImageRepository(BaseRepository[ReturnProofImage]):
    def __init__(self, db):
        super().__init__(ReturnProofImage, db)
