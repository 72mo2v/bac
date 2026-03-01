import sys
from os.path import dirname, abspath
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the app directory to the path so we can import our modules
sys.path.insert(0, dirname(dirname(abspath(__file__))))

from app.core.config import settings
from app.core.database import Base
# Import all models here so they are registered on the Base.metadata
from app.modules.auth.models import User, StoreUser, UserSession
from app.modules.stores.models import Store, StorePageViewDaily
from app.modules.products.models import Product, Category, Inventory, ProductImage
from app.modules.orders.models import Order, OrderItem, OrderHistory, ReturnRequest, ReturnProofImage
from app.modules.couriers.models import Courier
from app.modules.payments.models import OrderPayment, StorePaymentMethod, SubscriptionPayment, SubscriptionPaymentMethod, SubscriptionWebhook
from app.modules.notifications.models import Notification
from app.modules.audit.models import AuditLog
from app.modules.subscriptions.models import SubscriptionPlan, Subscription, Invoice
from app.modules.rbac.models import AdminRole, AdminUser, Permission, role_permissions
from app.modules.support.models import SupportTicket, TicketMessage
from app.modules.integrations.models import StoreBeroConnection, ProductExternalMapping, BeroSyncJob, BeroOutboxEvent


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set the sqlalchemy.url dynamically from settings
# Use the synchronous driver for alembic (psycopg2 or similar)
# Note: DATABASE_URL in settings uses asyncpg. 
# For migrations we should ideally use sync driver or configure async alembic.
# I'll convert the postgresql+asyncpg to postgresql (psycopg2) if needed.
sync_db_url = settings.DATABASE_URL.replace("asyncpg", "psycopg2") if settings.DATABASE_URL else ""
config.set_main_option("sqlalchemy.url", sync_db_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
