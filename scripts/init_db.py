import asyncio
from app.core.database import engine, Base
# Import all models to ensure they are registered with Base
from app.modules.products.models import Product, Category, Inventory, ProductReview, Cart, CartItem
from app.modules.stores.models import Store
from app.modules.auth.models import User
from app.modules.orders.models import Order, OrderItem
from app.modules.subscriptions.models import Subscription, SubscriptionPlan
from app.modules.support.models import SupportTicket, TicketMessage

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully!")

if __name__ == "__main__":
    asyncio.run(init_models())
