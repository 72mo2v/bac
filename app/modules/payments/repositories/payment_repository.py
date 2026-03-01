from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.base_repository import BaseRepository
from app.modules.payments.models import OrderPayment
from app.modules.orders.models import Order as OrderModel


class PaymentRepository(BaseRepository[OrderPayment]):
    def __init__(self, db):
        super().__init__(OrderPayment, db)

    async def get_with_method(self, payment_id: int) -> Optional[OrderPayment]:
        query = (
            select(OrderPayment)
            .options(
                selectinload(OrderPayment.store_payment_method),
                selectinload(OrderPayment.order).selectinload(OrderModel.customer),
            )
            .filter(OrderPayment.id == payment_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_order_id(self, order_id: int) -> Optional[OrderPayment]:
        query = select(OrderPayment).filter(OrderPayment.order_id == order_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
