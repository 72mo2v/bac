from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
from app.core.exceptions import BusinessRuleException, NotFoundException
from app.modules.payments.repositories.subscription_payment_repository import (
    SubscriptionPaymentRepository, 
    SubscriptionPaymentMethodRepository,
    SubscriptionWebhookRepository
)
from app.modules.subscriptions.repositories.subscription_repository import SubscriptionPlanRepository, SubscriptionRepository, InvoiceRepository
from app.modules.payments.services.providers.factory import ProviderFactory
from app.modules.subscriptions.models import SubscriptionStatus, InvoiceStatus

class SubscriptionPaymentService:
    def __init__(
        self, 
        payment_repo: SubscriptionPaymentRepository,
        method_repo: SubscriptionPaymentMethodRepository,
        webhook_repo: SubscriptionWebhookRepository,
        plan_repo: SubscriptionPlanRepository,
        subscription_repo: SubscriptionRepository,
        invoice_repo: InvoiceRepository
    ):
        self.payment_repo = payment_repo
        self.method_repo = method_repo
        self.webhook_repo = webhook_repo
        self.plan_repo = plan_repo
        self.subscription_repo = subscription_repo
        self.invoice_repo = invoice_repo

    async def initiate_payment(self, store_id: int, plan_id: int, method_id: int, success_url: str, cancel_url: str) -> Dict[str, Any]:
        # 1. Validate plan
        plan = await self.plan_repo.get(plan_id)
        if not plan or not plan.is_active:
            raise NotFoundException("Subscription plan not found or inactive")

        # 2. Validate payment method
        method = await self.method_repo.get(method_id)
        if not method or not method.is_enabled:
            raise BusinessRuleException("Payment method not available")

        # 3. Get or Create active subscription for store
        subscription = await self.subscription_repo.get_by_store_id(store_id)
        
        # 4. Create internal payment record
        payment_data = {
            "store_id": store_id,
            "subscription_id": subscription.id if subscription else None,
            "payment_method_id": method.id,
            "amount": plan.price,
            "currency": "EGP",
            "status": "pending"
        }
        payment = await self.payment_repo.create(payment_data)

        # 5. Initiate with provider
        provider = ProviderFactory.get_provider(method.provider, method.config)
        checkout_data = await provider.create_checkout_session(
            amount=float(plan.price),
            currency="egp",
            metadata={
                "payment_id": payment.id,
                "store_id": store_id,
                "plan_id": plan.id,
                "plan_name": plan.name,
                "success_url": success_url,
                "cancel_url": cancel_url
            }
        )

        # 6. Update payment with provider IDs
        await self.payment_repo.update(payment, {
            "payment_intent_id": checkout_data.get("provider_payment_intent"),
            "transaction_id": checkout_data.get("provider_session_id"),
            "provider_response": checkout_data
        })

        return {
            "payment_id": payment.id,
            "checkout_url": checkout_data.get("checkout_url")
        }

    async def handle_webhook(self, provider_name: str, payload: bytes, signature: str):
        # 1. Log webhook
        method = await self.method_repo.get_by_provider(provider_name)
        if not method:
            raise NotFoundException(f"Provider {provider_name} not configured")

        import json
        event_dict = json.loads(payload.decode('utf-8'))
        webhook_log = await self.webhook_repo.create({
            "provider": provider_name,
            "event_type": event_dict.get("type", "unknown"),
            "payload": event_dict,
            "signature": signature
        })

        # 2. Verify signature
        provider = ProviderFactory.get_provider(provider_name, method.config)
        is_valid = await provider.verify_webhook(payload, signature)
        if not is_valid:
            await self.webhook_repo.update(webhook_log, {"processing_error": "Invalid signature"})
            return

        # 3. Process event
        normalized = await provider.handle_webhook_event(event_dict)
        
        # 4. Find associated payment
        payment_id = normalized.get("metadata", {}).get("payment_id")
        payment = await self.payment_repo.get(int(payment_id)) if payment_id else None
        
        if not payment and normalized.get("payment_intent"):
            payment = await self.payment_repo.get_by_payment_intent(normalized.get("payment_intent"))

        if not payment:
            await self.webhook_repo.update(webhook_log, {"processed": True, "processing_error": "Payment record not found"})
            return

        await self.webhook_repo.update(webhook_log, {"payment_id": payment.id})

        # 5. Handle Status
        if normalized["status"] == "success":
            await self.process_success(payment, normalized)
        elif normalized["status"] == "failed":
            await self.process_failure(payment, normalized)

        await self.webhook_repo.update(webhook_log, {"processed": True})

    async def process_success(self, payment, provider_data):
        if payment.status == "success":
            return # Already processed

        # Update payment
        await self.payment_repo.update(payment, {
            "status": "success",
            "paid_at": datetime.now(),
            "provider_transaction_id": provider_data.get("transaction_id")
        })

        # Update Subscription
        metadata = provider_data.get("metadata", {})
        plan_id = int(metadata.get("plan_id"))
        plan = await self.plan_repo.get(plan_id)
        
        subscription = await self.subscription_repo.get_by_store_id(payment.store_id)
        
        if subscription:
            # Renew or upgrade
            new_end_date = max(subscription.end_date, datetime.now()) + timedelta(days=plan.duration_days)
            await self.subscription_repo.update(subscription, {
                "plan_id": plan.id,
                "status": SubscriptionStatus.ACTIVE,
                "end_date": new_end_date
            })
        else:
            # New subscription
            await self.subscription_repo.create({
                "store_id": payment.store_id,
                "plan_id": plan.id,
                "status": SubscriptionStatus.ACTIVE,
                "end_date": datetime.now() + timedelta(days=plan.duration_days)
            })

    async def process_failure(self, payment, provider_data):
        await self.payment_repo.update(payment, {
            "status": "failed",
            "failure_reason": provider_data.get("failure_reason")
        })
