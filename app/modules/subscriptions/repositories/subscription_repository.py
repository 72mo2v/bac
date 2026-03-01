from app.core.base_repository import BaseRepository
from app.modules.subscriptions.models import SubscriptionPlan, Subscription, Invoice

class SubscriptionPlanRepository(BaseRepository[SubscriptionPlan]):
    def __init__(self, db):
        super().__init__(SubscriptionPlan, db)

from typing import Optional
from sqlalchemy import select

class SubscriptionRepository(BaseRepository[Subscription]):
    def __init__(self, db):
        super().__init__(Subscription, db)

    async def get_by_store_id(self, store_id: int) -> Optional[Subscription]:
        query = select(Subscription).filter(Subscription.store_id == store_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

class InvoiceRepository(BaseRepository[Invoice]):
    def __init__(self, db):
        super().__init__(Invoice, db)
