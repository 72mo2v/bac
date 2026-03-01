from typing import Optional, List
from sqlalchemy import select
from app.core.base_repository import BaseRepository
from app.modules.payments.models import SubscriptionPayment, SubscriptionPaymentMethod, SubscriptionWebhook

from sqlalchemy.orm import joinedload

class SubscriptionPaymentRepository(BaseRepository[SubscriptionPayment]):
    def __init__(self, db):
        super().__init__(SubscriptionPayment, db)

    async def get_all_with_method(self) -> List[SubscriptionPayment]:
        query = select(SubscriptionPayment).options(joinedload(SubscriptionPayment.method))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_provider_transaction_id(self, transaction_id: str) -> Optional[SubscriptionPayment]:
        query = select(SubscriptionPayment).filter(SubscriptionPayment.transaction_id == transaction_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_payment_intent(self, payment_intent: str) -> Optional[SubscriptionPayment]:
        query = select(SubscriptionPayment).filter(SubscriptionPayment.payment_intent_id == payment_intent)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

class SubscriptionPaymentMethodRepository(BaseRepository[SubscriptionPaymentMethod]):
    def __init__(self, db):
        super().__init__(SubscriptionPaymentMethod, db)

    async def get_active_methods(self) -> List[SubscriptionPaymentMethod]:
        query = select(SubscriptionPaymentMethod).filter(SubscriptionPaymentMethod.is_enabled == True).order_by(SubscriptionPaymentMethod.display_order)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_provider(self, provider: str) -> Optional[SubscriptionPaymentMethod]:
        query = select(SubscriptionPaymentMethod).filter(SubscriptionPaymentMethod.provider == provider)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

class SubscriptionWebhookRepository(BaseRepository[SubscriptionWebhook]):
    def __init__(self, db):
        super().__init__(SubscriptionWebhook, db)
