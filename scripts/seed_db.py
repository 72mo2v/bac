import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.database import Base
from app.modules.products.models import Category, Product, Inventory, ProductReview
from app.modules.support.models import SupportTicket, TicketMessage, TicketStatus, TicketPriority, TicketCategory
from app.modules.stores.models import Store
from app.modules.subscriptions.models import Subscription, SubscriptionPlan
from app.modules.orders.models import Order, OrderItem
from app.modules.auth.models import User, UserRole
from app.core.security import get_password_hash

async def seed_data():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # Skip due to dependency issues
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Create test users
        users = []
        user_data = [
            {"email": "admin@tasoc.com", "full_name": "المدير العام", "password": "password123", "role": UserRole.SUPER_ADMIN},
            {"email": "customer1@gmail.com", "full_name": "أحمد محمد", "password": "password123", "role": UserRole.CUSTOMER},
            {"email": "customer2@gmail.com", "full_name": "سارة أحمد", "password": "password123", "role": UserRole.CUSTOMER},
        ]
        
        for u_data in user_data:
            hashed_pw = get_password_hash(u_data["password"])
            user = User(
                email=u_data["email"],
                full_name=u_data["full_name"],
                hashed_password=hashed_pw,
                role=u_data["role"],
                is_active=True
            )
            session.add(user)
            users.append(user)
        
        await session.flush()

        # Create a test store
        store = Store(
            name="المتجر الرئيسي",
            slug="main-store",
            description="متجرنا الرئيسي لجميع المنتجات",
            is_active=True
        )
        session.add(store)
        await session.flush()
        await session.refresh(store)

        # Create categories
        categories_data = [
            {"name": "إلكترونيات", "slug": "electronics", "store_id": store.id},
            {"name": "أزياء", "slug": "fashion", "store_id": store.id},
            {"name": "منزل ومطبخ", "slug": "home-kitchen", "store_id": store.id}
        ]
        
        categories = []
        for cat_data in categories_data:
            cat = Category(**cat_data)
            session.add(cat)
            categories.append(cat)
        
        await session.flush()
        for cat in categories:
            await session.refresh(cat)

        # Create products
        products_data = [
            {
                "name": "آيفون 15 برو",
                "slug": "iphone-15-pro",
                "price": 65000.0,
                "category_id": categories[0].id,
                "store_id": store.id,
                "image_url": "https://images.unsplash.com/photo-1696446701796-da61225697cc?w=800&q=80"
            },
            {
                "name": "سامسونج S24 ألترا",
                "slug": "samsung-s24-ultra",
                "price": 58000.0,
                "category_id": categories[0].id,
                "store_id": store.id,
                "image_url": "https://images.unsplash.com/photo-1707255140026-b9b59663673e?w=800&q=80"
            }
        ]

        for prod_data in products_data:
            prod = Product(**prod_data)
            session.add(prod)
            await session.flush()
            await session.refresh(prod)
            
            # Add inventory
            inv = Inventory(product_id=prod.id, store_id=store.id, quantity=100)
            session.add(inv)

            # Add sample reviews
            review1 = ProductReview(
                product_id=prod.id,
                user_id=users[1].id,
                rating=5,
                comment="منتج رائع جداً وأنصح به الجميع!"
            )
            review2 = ProductReview(
                product_id=prod.id,
                user_id=users[2].id,
                rating=4,
                comment="الجودة ممتازة ولكن الشحن تأخر قليلاً."
            )
            session.add(review1)
            session.add(review2)

        # Create sample support tickets
        ticket = SupportTicket(
            ticket_number="TKT-20260127-XYZ",
            customer_id=users[1].id,
            subject="مشكلة في توصيل الطلب",
            category=TicketCategory.SHIPPING,
            priority=TicketPriority.HIGH,
            status=TicketStatus.OPEN
        )
        session.add(ticket)
        await session.flush()

        message = TicketMessage(
            ticket_id=ticket.id,
            user_id=users[1].id,
            message="مرحباً، طلبي تأخر أكثر من ٣ أيام. هل يمكنكم التحقق؟"
        )
        session.add(message)

        await session.commit()
        print("Database seeded successfully with users, reviews and support tickets!")

if __name__ == "__main__":
    asyncio.run(seed_data())
