from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.auth.models import User
from app.modules.payments.subscription_schemas import SubscriptionPaymentInitiate, SubscriptionPayment, SubscriptionPaymentMethod
from app.modules.payments.repositories.subscription_payment_repository import (
    SubscriptionPaymentRepository, 
    SubscriptionPaymentMethodRepository,
    SubscriptionWebhookRepository
)
from app.modules.subscriptions.repositories.subscription_repository import (
    SubscriptionPlanRepository, 
    SubscriptionRepository,
    InvoiceRepository
)
from app.modules.payments.services.subscription_payment_service import SubscriptionPaymentService

router = APIRouter()

async def get_sub_payment_service(db: AsyncSession = Depends(get_db)) -> SubscriptionPaymentService:
    return SubscriptionPaymentService(
        payment_repo=SubscriptionPaymentRepository(db),
        method_repo=SubscriptionPaymentMethodRepository(db),
        webhook_repo=SubscriptionWebhookRepository(db),
        plan_repo=SubscriptionPlanRepository(db),
        subscription_repo=SubscriptionRepository(db),
        invoice_repo=InvoiceRepository(db)
    )

@router.get("/methods", response_model=List[SubscriptionPaymentMethod])
async def list_payment_methods(
    service: SubscriptionPaymentService = Depends(get_sub_payment_service)
):
    return await service.method_repo.get_active_methods()

@router.post("/initiate")
async def initiate_subscription_payment(
    data: SubscriptionPaymentInitiate,
    current_user: User = Depends(get_current_user),
    service: SubscriptionPaymentService = Depends(get_sub_payment_service)
):
    # Determine store_id from current_user memberships
    store_id = None
    if current_user.store_memberships:
        store_id = current_user.store_memberships[0].store_id
    
    if not store_id:
         from app.core.exceptions import BusinessRuleException
         raise BusinessRuleException("User is not associated with any store")
         
    return await service.initiate_payment(
        store_id=store_id,
        plan_id=data.plan_id,
        method_id=data.method_id,
        success_url=data.success_url,
        cancel_url=data.cancel_url
    )
