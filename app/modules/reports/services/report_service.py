from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.modules.stores.models import Store
from app.modules.orders.models import Order
from app.modules.auth.models import User

class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_admin_dashboard_summary(self):
        # 1. Total Stores count
        stores_query = select(func.count(Store.id))
        stores_count_result = await self.db.execute(stores_query)
        total_stores = stores_count_result.scalar()

        # 2. Total active stores
        active_stores_query = select(func.count(Store.id)).where(Store.is_active == True)
        active_stores_result = await self.db.execute(active_stores_query)
        active_stores = active_stores_result.scalar()

        # 3. Total Users count
        users_query = select(func.count(User.id))
        users_result = await self.db.execute(users_query)
        total_users = users_result.scalar()

        # 4. Total Orders and Revenue
        orders_query = select(func.count(Order.id), func.sum(Order.total_amount))
        orders_result = await self.db.execute(orders_query)
        orders_stats = orders_result.first()
        total_orders = orders_stats[0] if orders_stats else 0
        total_revenue = orders_stats[1] if orders_stats and orders_stats[1] else 0.0

        # 5. Revenue by Month (last 6 months)
        # Using extraction based on PostgreSQL/SQLite (may need adjustment depending on DB)
        revenue_query = select(
            func.date_trunc('month', Order.created_at).label('month'),
            func.sum(Order.total_amount).label('revenue')
        ).group_by('month').order_by('month').limit(6)
        
        revenue_result = await self.db.execute(revenue_query)
        revenue_by_month = [
            {"name": r.month.strftime('%B'), "value": float(r.revenue)} 
            for r in revenue_result.all() if r.month
        ]

        # 6. Orders by Status
        status_query = select(Order.status, func.count(Order.id)).group_by(Order.status)
        status_result = await self.db.execute(status_query)
        orders_by_status = {r.status.value: r[1] for r in status_result.all()}

        # 7. Subscriptions Metrics
        from app.modules.subscriptions.models import Subscription
        sub_query = select(Subscription.status, func.count(Subscription.id)).group_by(Subscription.status)
        sub_res = await self.db.execute(sub_query)
        sub_distribution = {r.status.value: r[1] for r in sub_res.all()}

        return {
            "total_stores": total_stores,
            "active_stores": active_stores,
            "total_users": total_users,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "revenue_data": revenue_by_month,
            "status_distribution": orders_by_status,
            "subscription_distribution": sub_distribution
        }

