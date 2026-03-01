from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.modules.subscriptions.models import SubscriptionStatus, InvoiceStatus, Subscription, SubscriptionPlan, Invoice
from app.modules.subscriptions.repositories.subscription_repository import (
    SubscriptionRepository, 
    SubscriptionPlanRepository, 
    InvoiceRepository
)

class SubscriptionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SubscriptionRepository(db)
        self.plan_repo = SubscriptionPlanRepository(db)
        self.invoice_repo = InvoiceRepository(db)

    async def get_plans(self, active_only: bool = True) -> List[SubscriptionPlan]:
        if active_only:
            from sqlalchemy import select
            query = select(SubscriptionPlan).filter(SubscriptionPlan.is_active == True)
            result = await self.db.execute(query)
            return result.scalars().all()
        return await self.plan_repo.get_all()

    async def get_by_store_id(self, store_id: int) -> Optional[Subscription]:
        from sqlalchemy import select
        query = select(Subscription).filter(Subscription.store_id == store_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_plan(self, plan_data: dict) -> SubscriptionPlan:
        return await self.plan_repo.create(plan_data)

    async def start_trial(self, store_id: int, plan_id: int) -> Subscription:
        # Check if store already has a subscription
        from sqlalchemy import select
        query = select(Subscription).filter(Subscription.store_id == store_id)
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise ValueError("Store already has a subscription")

        plan = await self.plan_repo.get(plan_id)
        if not plan:
            raise ValueError("Plan not found")
        
        now = datetime.now()
        trial_end = now + timedelta(days=plan.trial_days)
        
        subscription = Subscription(
            store_id=store_id,
            plan_id=plan_id,
            status=SubscriptionStatus.TRIAL,
            start_date=now,
            trial_end_date=trial_end,
            end_date=trial_end,
            auto_renew=True
        )
        
        self.db.add(subscription)
        await self.db.commit()
        await self.db.refresh(subscription)
        return subscription

    async def upgrade_subscription(self, subscription_id: int, plan_id: int) -> Subscription:
        subscription = await self.repo.get(subscription_id)
        if not subscription:
            raise ValueError("Subscription not found")

        plan = await self.plan_repo.get(plan_id)
        if not plan:
            raise ValueError("Plan not found")

        subscription.plan_id = plan_id
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.start_date = datetime.now()
        subscription.end_date = subscription.start_date + timedelta(days=plan.duration_days)
        subscription.trial_end_date = None

        await self.db.commit()
        await self.db.refresh(subscription)
        return subscription

    async def activate_subscription(self, subscription_id: int) -> Subscription:
        subscription = await self.repo.get(subscription_id)
        if not subscription:
            raise ValueError("Subscription not found")
        
        subscription.status = SubscriptionStatus.ACTIVE
        # Extend end date if it was just trial
        plan = await self.plan_repo.get(subscription.plan_id)
        subscription.end_date = datetime.now() + timedelta(days=plan.duration_days)
        
        await self.db.commit()
        await self.db.refresh(subscription)
        return subscription

    async def handle_invoice_payment(self, invoice_id: int, payment_ref: str, method: str) -> Invoice:
        invoice = await self.invoice_repo.get(invoice_id)
        if not invoice:
            raise ValueError("Invoice not found")
        
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = datetime.now()
        invoice.payment_reference = payment_ref
        invoice.payment_method = method
        
        # Update subscription status
        await self.activate_subscription(invoice.subscription_id)
        
        await self.db.commit()
        await self.db.refresh(invoice)
        return invoice

    async def suspend_subscription(self, subscription_id: int) -> Subscription:
        subscription = await self.repo.get(subscription_id)
        if not subscription:
            raise ValueError("Subscription not found")
        
        subscription.status = SubscriptionStatus.SUSPENDED
        await self.db.commit()
        await self.db.refresh(subscription)
        return subscription

    async def update_plan(self, plan_id: int, plan_data: dict) -> SubscriptionPlan:
        plan = await self.plan_repo.get(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        updated_plan = await self.plan_repo.update(plan, plan_data)
        await self.db.commit()
        await self.db.refresh(updated_plan)
        return updated_plan

    async def delete_subscription(self, subscription_id: int) -> None:
        subscription = await self.repo.get(subscription_id)
        if not subscription:
            raise ValueError("Subscription not found")
        
        # Delete related invoices first to avoid FK constraints
        from sqlalchemy import delete
        from app.modules.subscriptions.models import Invoice
        await self.db.execute(delete(Invoice).where(Invoice.subscription_id == subscription_id))
        
        await self.repo.remove(subscription_id)
        await self.db.commit()

    async def delete_plan(self, plan_id: int) -> None:
        # Check if any subscriptions are using this plan
        from sqlalchemy import select, func
        query = select(func.count(Subscription.id)).where(Subscription.plan_id == plan_id)
        result = await self.db.execute(query)
        count = result.scalar()
        
        if count > 0:
            raise ValueError("Cannot delete plan: This plan is currently used by one or more active subscriptions.")
        
        await self.plan_repo.remove(plan_id)
        await self.db.commit()
