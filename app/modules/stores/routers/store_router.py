from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from pathlib import Path
import uuid
from datetime import date, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import ProgrammingError
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.modules.auth.models import User, UserRole, StoreUser
from app.core.middleware import get_store_id
from app.modules.orders.models import Order, OrderStatus
from app.modules.products.models import Product, Inventory
from app.modules.couriers.models import Courier, CourierStatus
from app.modules.subscriptions.models import Subscription
from app.modules.payments.schemas import StorePaymentMethod, StorePaymentMethodCreate, StorePaymentMethodUpdate, Payment
from app.modules.payments.repositories.store_payment_repository import StorePaymentMethodRepository
from app.modules.payments.repositories.payment_repository import PaymentRepository
from app.modules.payments.services.store_payment_service import StorePaymentMethodService
from app.modules.products.models import ProductReview, Product
from app.modules.products.schemas import StoreReviewList, StoreReviewStats, ReviewReport
from app.modules.stores.schemas import Store, StoreCreate, StoreUpdate, StoreDashboardStats, StoreDashboardStatsToday, StoreDashboardStatsCurrent, StoreVerificationSubmit, StoreMembership
from app.modules.stores.models import StoreVerificationStatus, StorePageViewDaily
from app.modules.stores.repositories.store_repository import StoreRepository
from app.modules.stores.services.store_service import StoreService
from app.modules.notifications.repositories.notification_repository import NotificationRepository
from app.modules.notifications.services.notification_service import NotificationService
from app.modules.integrations.bero_service import BeroIntegrationService
from app.modules.integrations.schemas import (
    BeroConnectRequest,
    BeroConnectResponse,
    BeroConnectionStatusResponse,
    BeroSyncNowResponse,
)
from app.modules.orders.models import OrderItem
from app.modules.products.models import Category

router = APIRouter()


def _make_series(days: int) -> list[date]:
    today = date.today()
    start = today - timedelta(days=days - 1)
    return [start + timedelta(days=i) for i in range(days)]


async def _resolve_store_id(db: AsyncSession, current_user: User) -> int:
    ctx_store_id = get_store_id()
    if ctx_store_id:
        if current_user.role != UserRole.SUPER_ADMIN:
            membership = await db.execute(
                select(func.count(StoreUser.id)).where(
                    StoreUser.user_id == current_user.id,
                    StoreUser.store_id == ctx_store_id,
                )
            )
            if int(membership.scalar() or 0) == 0:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Store access denied")
        return int(ctx_store_id)

    result = await db.execute(
        select(StoreUser.store_id).where(StoreUser.user_id == current_user.id).order_by(StoreUser.store_id.asc())
    )
    store_id = result.scalars().first()
    if not store_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No store associated with this user")
    return int(store_id)

async def get_store_service(db: AsyncSession = Depends(get_db)) -> StoreService:
    repo = StoreRepository(db)
    return StoreService(repo)

async def get_store_payment_service(db: AsyncSession = Depends(get_db)) -> StorePaymentMethodService:
    repo = StorePaymentMethodRepository(db)
    return StorePaymentMethodService(repo)


async def get_bero_service(db: AsyncSession = Depends(get_db)) -> BeroIntegrationService:
    return BeroIntegrationService(db)

@router.post("/", response_model=Store)
async def create_store(
    store_in: StoreCreate,
    service: StoreService = Depends(get_store_service)
):
    return await service.create_store(store_in)

@router.post("/me", response_model=Store)
async def create_my_store(
    store_in: StoreCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    existing_membership = await db.execute(
        select(StoreUser.store_id).where(StoreUser.user_id == current_user.id).order_by(StoreUser.store_id.asc())
    )
    existing_store_id = existing_membership.scalars().first()
    if existing_store_id:
        existing_store = await StoreRepository(db).get(int(existing_store_id))
        if existing_store and getattr(existing_store, "is_active", True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have an active store",
            )

    service = await get_store_service(db)
    store = await service.create_store(store_in)

    membership = StoreUser(user_id=current_user.id, store_id=store.id, role=UserRole.STORE_OWNER)
    db.add(membership)

    if current_user.role != UserRole.SUPER_ADMIN and current_user.role != UserRole.STORE_OWNER:
        current_user.role = UserRole.STORE_OWNER
        db.add(current_user)

    await db.flush()
    return store

@router.get("/me/dashboard/stats", response_model=StoreDashboardStats)
async def get_my_store_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    store_id = await _resolve_store_id(db, current_user)

    today = date.today()

    orders_today_count_result = await db.execute(
        select(func.count(Order.id)).where(
            Order.store_id == store_id,
            func.date(Order.created_at) == today,
        )
    )
    orders_today_count = int(orders_today_count_result.scalar() or 0)

    revenue_today_result = await db.execute(
        select(func.coalesce(func.sum(Order.total_amount), 0)).where(
            Order.store_id == store_id,
            func.date(Order.created_at) == today,
        )
    )
    revenue_today = float(revenue_today_result.scalar() or 0)

    active_products_result = await db.execute(
        select(func.count(Product.id)).where(
            Product.store_id == store_id,
            Product.is_active.is_(True),
        )
    )
    active_products = int(active_products_result.scalar() or 0)

    low_stock_result = await db.execute(
        select(func.count(Inventory.id)).where(
            Inventory.store_id == store_id,
            Inventory.quantity <= Inventory.low_stock_threshold,
        )
    )
    low_stock_products = int(low_stock_result.scalar() or 0)

    pending_orders_result = await db.execute(
        select(func.count(Order.id)).where(
            Order.store_id == store_id,
            Order.status == OrderStatus.PENDING,
        )
    )
    pending_orders = int(pending_orders_result.scalar() or 0)

    active_couriers_result = await db.execute(
        select(func.count(Courier.id)).where(
            Courier.store_id == store_id,
            Courier.status == CourierStatus.ACTIVE,
        )
    )
    active_couriers = int(active_couriers_result.scalar() or 0)

    busy_couriers_result = await db.execute(
        select(func.count(Courier.id)).where(
            Courier.store_id == store_id,
            Courier.status == CourierStatus.ACTIVE,
            Courier.is_available.is_(False),
        )
    )
    busy_couriers = int(busy_couriers_result.scalar() or 0)

    subscription_status = None
    subscription_days_left = None
    sub_result = await db.execute(select(Subscription).where(Subscription.store_id == store_id))
    subscription = sub_result.scalar_one_or_none()
    if subscription:
        subscription_status = str(subscription.status.value) if subscription.status else None
        if subscription.end_date:
            subscription_days_left = (subscription.end_date.date() - today).days

    return StoreDashboardStats(
        today=StoreDashboardStatsToday(
            orders_count=orders_today_count,
            revenue=revenue_today,
        ),
        current=StoreDashboardStatsCurrent(
            active_products=active_products,
            low_stock_products=low_stock_products,
            pending_orders=pending_orders,
            active_couriers=active_couriers,
            busy_couriers=busy_couriers,
        ),
        subscription_status=subscription_status,
        subscription_days_left=subscription_days_left,
    )


@router.get("/me/dashboard/sales")
async def get_my_store_dashboard_sales(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="days must be between 1 and 90")

    store_id = await _resolve_store_id(db, current_user)

    series_days = _make_series(days)
    sales_by_day = {d: 0.0 for d in series_days}

    rows = await db.execute(
        select(func.date(Order.created_at).label("day"), func.coalesce(func.sum(Order.total_amount), 0).label("sales"))
        .where(
            Order.store_id == store_id,
            func.date(Order.created_at) >= series_days[0],
            func.date(Order.created_at) <= series_days[-1],
        )
        .group_by("day")
        .order_by("day")
    )

    for r in rows.all():
        if r.day in sales_by_day:
            sales_by_day[r.day] = float(r.sales or 0)

    # Return same shape as existing UI expects: [{ name, sales }]
    data = [{"name": d.strftime("%Y-%m-%d"), "sales": sales_by_day[d]} for d in series_days]
    return {"days": days, "data": data}


@router.get("/me/reports/summary")
async def get_my_store_reports_summary(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="days must be between 1 and 365")

    store_id = await _resolve_store_id(db, current_user)

    today = date.today()
    start_day = today - timedelta(days=days - 1)

    # Sales + orders
    totals = await db.execute(
        select(
            func.count(Order.id).label("orders"),
            func.coalesce(func.sum(Order.total_amount), 0).label("sales"),
        ).where(
            Order.store_id == store_id,
            func.date(Order.created_at) >= start_day,
            func.date(Order.created_at) <= today,
        )
    )
    totals_row = totals.one()
    total_orders = int(totals_row.orders or 0)
    total_sales = float(totals_row.sales or 0)

    # Unique customers in period
    customers = await db.execute(
        select(func.count(func.distinct(Order.customer_id))).where(
            Order.store_id == store_id,
            func.date(Order.created_at) >= start_day,
            func.date(Order.created_at) <= today,
        )
    )
    unique_customers = int(customers.scalar() or 0)

    # Weekly sales (4 buckets)
    bucket_days = max(1, days // 4)
    weekly_data = []
    for i in range(4):
        b_start = start_day + timedelta(days=i * bucket_days)
        b_end = start_day + timedelta(days=min(days - 1, (i + 1) * bucket_days - 1))
        res = await db.execute(
            select(
                func.coalesce(func.sum(Order.total_amount), 0).label("sales"),
                func.count(Order.id).label("orders"),
            ).where(
                Order.store_id == store_id,
                func.date(Order.created_at) >= b_start,
                func.date(Order.created_at) <= b_end,
            )
        )
        row = res.one()
        weekly_data.append(
            {
                "name": f"{i+1}",
                "sales": float(row.sales or 0),
                "orders": int(row.orders or 0),
            }
        )

    # Category distribution by quantity sold
    cat_rows = await db.execute(
        select(Category.name, func.coalesce(func.sum(OrderItem.quantity), 0).label("qty"))
        .join(Product, Product.id == OrderItem.product_id)
        .join(Category, Category.id == Product.category_id, isouter=True)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.store_id == store_id,
            func.date(Order.created_at) >= start_day,
            func.date(Order.created_at) <= today,
        )
        .group_by(Category.name)
        .order_by(func.coalesce(func.sum(OrderItem.quantity), 0).desc())
    )
    category_distribution = [
        {"name": (r[0] or "غير مصنف"), "value": int(r.qty or 0)} for r in cat_rows.all()
    ]

    # Top products
    prod_rows = await db.execute(
        select(
            Product.id,
            Product.name,
            func.coalesce(func.sum(OrderItem.quantity), 0).label("qty"),
            func.coalesce(func.sum(OrderItem.total_price), 0).label("revenue"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Product.store_id == store_id,
            func.date(Order.created_at) >= start_day,
            func.date(Order.created_at) <= today,
        )
        .group_by(Product.id, Product.name)
        .order_by(func.coalesce(func.sum(OrderItem.quantity), 0).desc())
        .limit(10)
    )
    top_products = [
        {
            "id": int(r.id),
            "name": r.name,
            "sales": int(r.qty or 0),
            "revenue": float(r.revenue or 0),
        }
        for r in prod_rows.all()
    ]

    # Visits count
    try:
        visits_res = await db.execute(
            select(func.coalesce(func.sum(StorePageViewDaily.visits), 0)).where(
                StorePageViewDaily.store_id == store_id,
                StorePageViewDaily.day >= start_day,
                StorePageViewDaily.day <= today,
            )
        )
        visits_count = int(visits_res.scalar() or 0)
    except ProgrammingError:
        # In case migrations weren't applied yet
        visits_count = 0

    return {
        "days": days,
        "totals": {
            "total_sales": total_sales,
            "total_orders": total_orders,
            "unique_customers": unique_customers,
            "visits_count": visits_count,
        },
        "weekly_sales": weekly_data,
        "category_distribution": category_distribution,
        "top_products": top_products,
    }


@router.get("/me", response_model=Store)
async def get_my_store(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    store_id = await _resolve_store_id(db, current_user)

    service = await get_store_service(db)
    return await service.get_store(store_id)


@router.put("/me", response_model=Store)
@router.put("/me/", response_model=Store)
async def update_my_store(
    payload: StoreUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    store_id = await _resolve_store_id(db, current_user)

    service = await get_store_service(db)
    store = await service.get_store(store_id)

    updated = await service.store_repo.update(store, payload.model_dump(exclude_unset=True))
    await db.commit()
    return updated


@router.post("/me/integrations/bero/connect", response_model=BeroConnectResponse)
async def connect_bero(
    payload: BeroConnectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    bero_service: BeroIntegrationService = Depends(get_bero_service),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")
    store_id = await _resolve_store_id(db, current_user)
    result = await bero_service.connect(store_id, payload)
    await db.commit()
    return BeroConnectResponse(**result)


@router.get("/me/integrations/bero/status", response_model=BeroConnectionStatusResponse)
async def get_bero_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    bero_service: BeroIntegrationService = Depends(get_bero_service),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")
    store_id = await _resolve_store_id(db, current_user)
    result = await bero_service.get_status(store_id)
    return BeroConnectionStatusResponse(**result)


@router.post("/me/integrations/bero/sync-now", response_model=BeroSyncNowResponse)
async def sync_bero_now(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    bero_service: BeroIntegrationService = Depends(get_bero_service),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")
    store_id = await _resolve_store_id(db, current_user)
    synced = await bero_service.sync_products(store_id)
    await db.commit()
    return BeroSyncNowResponse(status="SUCCESS", synced_products=synced, message=f"Synced {synced} products")


@router.post("/me/integrations/bero/disconnect")
async def disconnect_bero(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    bero_service: BeroIntegrationService = Depends(get_bero_service),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")
    store_id = await _resolve_store_id(db, current_user)
    await bero_service.disconnect(store_id)
    await db.commit()
    return {"status": "SUCCESS", "message": "Bero disconnected"}


@router.post("/me/logo/upload", response_model=Store)
async def upload_my_store_logo(
    request: Request,
    logo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    store_id = await _resolve_store_id(db, current_user)

    service = await get_store_service(db)
    store = await service.get_store(store_id)

    uploads_dir = Path(__file__).resolve().parents[4] / "uploads" / "store_logos" / str(store_id)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    def _build_public_url(relative_path: str) -> str:
        base = str(request.base_url).rstrip("/")
        return f"{base}/uploads/{relative_path.lstrip('/')}"

    suffix = Path(logo.filename or "").suffix.lower()
    if suffix not in [".png", ".jpg", ".jpeg", ".webp"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    content = await logo.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")

    safe_name = f"{uuid.uuid4().hex}{suffix}"
    dest = uploads_dir / safe_name
    dest.write_bytes(content)
    rel = f"store_logos/{store_id}/{safe_name}"

    updated = await service.store_repo.update(store, {"logo_url": _build_public_url(rel)})
    await db.commit()
    return updated


@router.get("/me/memberships", response_model=List[StoreMembership])
async def list_my_store_memberships(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    result = await db.execute(
        select(StoreUser, StoreService(StoreRepository(db)).store_repo.model)
        .join(StoreService(StoreRepository(db)).store_repo.model, StoreService(StoreRepository(db)).store_repo.model.id == StoreUser.store_id)
        .where(StoreUser.user_id == current_user.id)
        .order_by(StoreUser.store_id.asc())
    )
    rows = result.all()
    return [StoreMembership(store=row[1], role=row[0].role) for row in rows]


@router.get("/me/reviews", response_model=StoreReviewList)
async def list_store_reviews(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    store_id = await _resolve_store_id(db, current_user)

    result = await db.execute(
        select(ProductReview)
        .join(Product, Product.id == ProductReview.product_id)
        .where(Product.store_id == store_id)
        .order_by(ProductReview.created_at.desc())
    )
    reviews = list(result.scalars().all())

    stats_result = await db.execute(
        select(func.count(ProductReview.id), func.avg(ProductReview.rating))
        .join(Product, Product.id == ProductReview.product_id)
        .where(Product.store_id == store_id)
    )
    total_count, avg_rating = stats_result.one()

    dist_result = await db.execute(
        select(ProductReview.rating, func.count(ProductReview.id))
        .join(Product, Product.id == ProductReview.product_id)
        .where(Product.store_id == store_id)
        .group_by(ProductReview.rating)
    )
    rating_distribution = {row[0]: row[1] for row in dist_result.all()}

    stats = StoreReviewStats(
        average_rating=float(avg_rating or 0),
        total_reviews=int(total_count or 0),
        rating_distribution=rating_distribution,
    )

    return StoreReviewList(reviews=reviews, stats=stats)


@router.post("/reviews/{review_id}/report")
async def report_review(
    review_id: int,
    payload: ReviewReport,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    store_id = await _resolve_store_id(db, current_user)

    result = await db.execute(
        select(ProductReview)
        .join(Product, Product.id == ProductReview.product_id)
        .where(Product.store_id == store_id, ProductReview.id == review_id)
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.is_reported = True
    review.report_reason = payload.reason
    review.reported_at = datetime.utcnow()
    db.add(review)
    await db.commit()
    return {"status": "success"}


@router.get("/me/payment-methods", response_model=List[StorePaymentMethod])
async def list_store_payment_methods(
    current_user: User = Depends(get_current_active_user),
    service: StorePaymentMethodService = Depends(get_store_payment_service),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER]:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    store_id = await _resolve_store_id(db, current_user)
    return await service.get_methods_for_store(store_id)


@router.post("/me/payment-methods", response_model=StorePaymentMethod)
async def create_store_payment_method(
    payload: StorePaymentMethodCreate,
    current_user: User = Depends(get_current_active_user),
    service: StorePaymentMethodService = Depends(get_store_payment_service),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER]:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    store_id = await _resolve_store_id(db, current_user)
    return await service.create_method(store_id, payload)


@router.put("/me/payment-methods/{method_id}", response_model=StorePaymentMethod)
async def update_store_payment_method(
    method_id: int,
    payload: StorePaymentMethodUpdate,
    current_user: User = Depends(get_current_active_user),
    service: StorePaymentMethodService = Depends(get_store_payment_service),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER]:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    store_id = await _resolve_store_id(db, current_user)
    return await service.update_method(store_id, method_id, payload)


@router.delete("/me/payment-methods/{method_id}")
async def delete_store_payment_method(
    method_id: int,
    current_user: User = Depends(get_current_active_user),
    service: StorePaymentMethodService = Depends(get_store_payment_service),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER]:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    store_id = await _resolve_store_id(db, current_user)
    await service.delete_method(store_id, method_id)
    return {"status": "success"}


@router.get("/me/transactions", response_model=List[Payment])
async def list_store_transactions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    store_id = await _resolve_store_id(db, current_user)
    result = await db.execute(
        select(PaymentRepository(db).model)
        .where(PaymentRepository(db).model.store_id == store_id)
        .order_by(PaymentRepository(db).model.created_at.desc())
    )
    return list(result.scalars().all())


@router.put("/me/verification", response_model=Store)
async def submit_my_store_verification(
    payload: StoreVerificationSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    store_id = await _resolve_store_id(db, current_user)

    service = await get_store_service(db)
    store = await service.get_store(store_id)

    update_data = payload.model_dump(exclude_unset=True)
    update_data["verification_status"] = StoreVerificationStatus.UNDER_REVIEW

    updated = await service.store_repo.update(store, update_data)
    await db.commit()

    # Notify admins
    notif_service = NotificationService(NotificationRepository(db))
    admin_users = await db.execute(
        select(User).where(User.role == UserRole.SUPER_ADMIN)
    )
    for admin in list(admin_users.scalars().all()):
        await notif_service.notify_user(
            user_id=admin.id,
            title="طلب توثيق متجر جديد",
            message=f"تم إرسال طلب توثيق لمتجر {updated.name} ({updated.slug}).",
            type="warning",
            data={"store_id": updated.id, "slug": updated.slug},
            store_id=None,
        )
    return updated


@router.post("/me/verification/upload", response_model=Store)
async def upload_my_store_verification_documents(
    request: Request,
    commercial_registration: Optional[UploadFile] = File(None),
    id_card: Optional[UploadFile] = File(None),
    store_front: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    store_id = await _resolve_store_id(db, current_user)

    service = await get_store_service(db)
    store = await service.get_store(store_id)

    uploads_dir = Path(__file__).resolve().parents[4] / "uploads" / "store_verification" / str(store_id)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    def _build_public_url(relative_path: str) -> str:
        base = str(request.base_url).rstrip("/")
        return f"{base}/uploads/{relative_path.lstrip('/')}"

    async def _save(file: UploadFile) -> str:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in [".png", ".jpg", ".jpeg", ".webp", ".pdf"]:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        safe_name = f"{uuid.uuid4().hex}{suffix}"
        dest = uploads_dir / safe_name
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large")
        dest.write_bytes(content)
        rel = f"store_verification/{store_id}/{safe_name}"
        return _build_public_url(rel)

    update_data = {}
    if commercial_registration:
        update_data["commercial_registration_url"] = await _save(commercial_registration)
    if id_card:
        update_data["id_card_url"] = await _save(id_card)
    if store_front:
        update_data["store_front_photo_url"] = await _save(store_front)

    if not update_data:
        raise HTTPException(status_code=400, detail="No files provided")

    update_data["verification_status"] = StoreVerificationStatus.UNDER_REVIEW

    updated = await service.store_repo.update(store, update_data)
    await db.commit()

    # Notify admins (documents uploaded)
    notif_service = NotificationService(NotificationRepository(db))
    admin_users = await db.execute(
        select(User).where(User.role == UserRole.SUPER_ADMIN)
    )
    for admin in list(admin_users.scalars().all()):
        await notif_service.notify_user(
            user_id=admin.id,
            title="تم رفع مستندات توثيق متجر",
            message=f"تم رفع مستندات توثيق لمتجر {updated.name} ({updated.slug}).",
            type="info",
            data={"store_id": updated.id, "slug": updated.slug},
            store_id=None,
        )
    return updated

@router.get("/{store_id}", response_model=Store)
async def get_store(
    store_id: int,
    service: StoreService = Depends(get_store_service)
):
    return await service.get_store(store_id)


@router.post("/{store_id}/visit")
async def record_store_visit(
    store_id: int,
    db: AsyncSession = Depends(get_db),
):
    # Public endpoint: increments store visit count for today
    today = date.today()

    store = await StoreRepository(db).get(store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    existing = await db.execute(
        select(StorePageViewDaily).where(StorePageViewDaily.store_id == store_id, StorePageViewDaily.day == today)
    )
    row = existing.scalar_one_or_none()
    if row:
        row.visits = int(row.visits or 0) + 1
        db.add(row)
    else:
        db.add(StorePageViewDaily(store_id=store_id, day=today, visits=1))

    await db.commit()
    return {"status": "success"}

@router.get("/", response_model=List[Store])
async def list_stores(
    skip: int = 0,
    limit: int = 100,
    service: StoreService = Depends(get_store_service)
):
    return await service.store_repo.get_multi(skip=skip, limit=limit)

@router.put("/{store_id}", response_model=Store)
async def update_store(
    store_id: int,
    store_in: StoreUpdate,
    service: StoreService = Depends(get_store_service)
):
    return await service.update_store(store_id, store_in)
