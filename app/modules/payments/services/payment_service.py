from app.core.exceptions import BusinessRuleException, NotFoundException
from app.modules.payments.repositories.payment_repository import PaymentRepository
from app.modules.orders.repositories.order_repository import OrderRepository
from app.modules.payments.schemas import PaymentCreate, PaymentUpdate
from app.modules.payments.models import PaymentStatus

class PaymentService:
    def __init__(self, payment_repo: PaymentRepository, order_repo: OrderRepository):
        self.payment_repo = payment_repo
        self.order_repo = order_repo

    async def create_payment(self, payment_in: PaymentCreate):
        # 1. Check if order exists
        order = await self.order_repo.get(payment_in.order_id)
        if not order:
            raise NotFoundException("Order not found")
        
        # 2. Check if payment already exists for this order
        existing = await self.payment_repo.get_by_order_id(payment_in.order_id)
        if existing:
            raise BusinessRuleException("Payment already initiated for this order")
            
        payment_data = payment_in.model_dump()
        payment_data["amount"] = order.total_amount
        payment_data["store_id"] = order.store_id
        payment_data["status"] = PaymentStatus.PENDING
        
        created = await self.payment_repo.create(payment_data)
        return await self.payment_repo.get_with_method(created.id) or created

    async def process_payment(self, payment_id: int, update: PaymentUpdate):
        payment = await self.payment_repo.get(payment_id)
        if not payment:
            raise NotFoundException("Payment not found")
            
        updated_payment = await self.payment_repo.update(payment, update.model_dump(exclude_unset=True))
        
        if updated_payment.status == PaymentStatus.COMPLETED:
            # Update order payment status
            order = await self.order_repo.get(payment.order_id)
            if order:
                order.is_paid = True
                await self.order_repo.update(order, {})
                
        return await self.payment_repo.get_with_method(updated_payment.id) or updated_payment
