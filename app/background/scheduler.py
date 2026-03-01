from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

def setup_scheduler():
    from app.background.tasks import (
        check_expired_subscriptions, 
        send_renewal_reminders, 
        generate_monthly_invoices,
        run_bero_incremental_sync,
        process_bero_outbox_events,
    )
    
    # Run daily at midnight
    scheduler.add_job(check_expired_subscriptions, 'cron', hour=0, minute=0, id='check_expired_subs', replace_existing=True)
    
    # Run daily at 9 AM
    scheduler.add_job(send_renewal_reminders, 'cron', hour=9, minute=0, id='renewal_reminders', replace_existing=True)
    
    # Run monthly on the 1st
    scheduler.add_job(generate_monthly_invoices, 'cron', day=1, hour=0, id='monthly_invoices', replace_existing=True)

    # Run Bero sync and outbox every minute
    scheduler.add_job(run_bero_incremental_sync, 'interval', minutes=1, id='bero_incremental_sync', replace_existing=True)
    scheduler.add_job(process_bero_outbox_events, 'interval', minutes=1, id='bero_outbox', replace_existing=True)
    
    logger.info("Initializing Background Scheduler...")
    scheduler.start()
    logger.info("Scheduler Started.")

def shutdown_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler Shutdown.")
