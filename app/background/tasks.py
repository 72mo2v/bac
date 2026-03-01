from app.core.database import AsyncSessionLocal
from app.modules.subscriptions.services.subscription_service import SubscriptionService
from app.modules.subscriptions.models import Subscription, SubscriptionStatus
from sqlalchemy import select
from datetime import datetime, timedelta
import logging
from app.modules.integrations.bero_service import BeroIntegrationService
from app.modules.integrations.models import StoreBeroConnection

logger = logging.getLogger(__name__)

async def check_expired_subscriptions():
    logger.info("Executing task: check_expired_subscriptions")
    async with AsyncSessionLocal() as db:
        query = select(Subscription).filter(
            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
            Subscription.end_date <= datetime.now()
        )
        result = await db.execute(query)
        expired_subs = result.scalars().all()
        
        service = SubscriptionService(db)
        for sub in expired_subs:
            logger.info(f"Suspending subscription {sub.id} for store {sub.store_id}")
            await service.suspend_subscription(sub.id)
        
        await db.commit()

async def send_renewal_reminders():
    logger.info("Executing task: send_renewal_reminders")
    # Reminder 7 days before expiry
    target_date = datetime.now() + timedelta(days=7)
    async with AsyncSessionLocal() as db:
        query = select(Subscription).filter(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.end_date <= target_date,
            Subscription.end_date > datetime.now()
        )
        result = await db.execute(query)
        expiring_soon = result.scalars().all()
        
        for sub in expiring_soon:
            logger.info(f"Sending reminder to store {sub.store_id} - expiring on {sub.end_date}")
            # TODO: Integrate with notification service once implemented in Phase 3

async def generate_monthly_invoices():
    logger.info("Executing task: generate_monthly_invoices")
    # This usually runs on the 1st of each month or on subscription anniversary
    # For simplicity, we can query active subscriptions that are auto-renewing
    async with AsyncSessionLocal() as db:
        query = select(Subscription).filter(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.auto_renew == True
        )
        # Logic to check if invoice already exists for next period...
        pass


async def run_bero_incremental_sync():
    logger.info("Executing task: run_bero_incremental_sync")
    async with AsyncSessionLocal() as db:
        rows = await db.execute(
            select(StoreBeroConnection).where(
                StoreBeroConnection.is_active.is_(True),
                StoreBeroConnection.status == "CONNECTED",
            )
        )
        connections = rows.scalars().all()
        service = BeroIntegrationService(db)
        for conn in connections:
            try:
                await service.sync_products(int(conn.store_id))
            except Exception as exc:
                logger.exception("Bero sync failed for store_id=%s: %s", conn.store_id, exc)
        await db.commit()


async def process_bero_outbox_events():
    logger.info("Executing task: process_bero_outbox_events")
    async with AsyncSessionLocal() as db:
        service = BeroIntegrationService(db)
        try:
            sent = await service.process_outbox()
            logger.info("Bero outbox processed; sent=%s", sent)
        except Exception as exc:
            logger.exception("Bero outbox processing failed: %s", exc)
        await db.commit()
