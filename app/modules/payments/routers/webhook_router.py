from fastapi import APIRouter, Depends, Request, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
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

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    service: SubscriptionPaymentService = Depends(get_sub_payment_service)
):
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")
        
    payload = await request.body()
    await service.handle_webhook("stripe", payload, stripe_signature)
    return {"status": "received"}

@router.post("/paypal")
async def paypal_webhook(
    request: Request,
    service: SubscriptionPaymentService = Depends(get_sub_payment_service)
):
    payload = await request.body()
    # PayPal signature verification logic would go here
    await service.handle_webhook("paypal", payload, "paypal-signature-placeholder")
    return {"status": "received"}
