from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from pathlib import Path
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from sqlalchemy import select, func
from app.modules.orders.schemas import (
    Order,
    OrderCreate,
    OrderStatusUpdate,
    PendingOrdersCount,
    AssignCourierRequest,
    ReturnRequest,
    ReturnRequestBase,
    ReturnRequestCreate,
    ReturnRequestReview,
)
from app.modules.orders.repositories.order_repository import (
    OrderRepository,
    OrderHistoryRepository,
    ReturnRequestRepository,
    ReturnProofImageRepository,
)
from app.modules.products.repositories.product_repository import ProductRepository
from app.modules.orders.services.order_service import OrderService
from app.core.deps import get_current_user, get_current_active_user, require_current_store_id
from app.core.middleware import get_store_id
from app.modules.auth.models import User as AuthUser, UserRole, StoreUser
from app.modules.orders.models import Order as OrderModel, OrderStatus, ReturnStatus, ReturnRequest as ReturnRequestModel
from app.modules.products.models import Inventory as InventoryModel
from datetime import datetime
from app.modules.couriers.models import Courier as CourierModel, CourierStatus
from app.modules.notifications.repositories.notification_repository import NotificationRepository
from app.modules.notifications.services.notification_service import NotificationService

router = APIRouter()


async def _resolve_store_id(db: AsyncSession, current_user: AuthUser) -> int:
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

    result = await db.execute(select(StoreUser.store_id).where(StoreUser.user_id == current_user.id))
    store_ids = list(result.scalars().all())
    if not store_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No store associated with this user")
    if len(store_ids) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multiple stores associated with this user. Please specify X-Store-Id header.",
        )
    return int(store_ids[0])


async def get_order_service(db: AsyncSession = Depends(get_db)) -> OrderService:
    order_repo = OrderRepository(db)
    prod_repo = ProductRepository(db)
    history_repo = OrderHistoryRepository(db)
    return OrderService(order_repo, prod_repo, history_repo)

# Removed Mock Current User

@router.post("/", response_model=Order)
async def create_order(
    order_in: OrderCreate,
    service: OrderService = Depends(get_order_service),
    current_user: AuthUser = Depends(get_current_user)
):
    created = await service.create_order(order_in, current_user.id)

    try:
        store_id = int(getattr(created, "store_id", None) or 0)
        if store_id:
            db = service.order_repo.db
            result = await db.execute(
                select(StoreUser.user_id)
                .where(StoreUser.store_id == store_id)
                .where(StoreUser.role.in_([UserRole.STORE_OWNER, UserRole.STORE_ADMIN]))
            )
            merchant_user_ids = list({int(x) for x in result.scalars().all() if x is not None})
            if merchant_user_ids:
                notif_service = NotificationService(NotificationRepository(db))
                for uid in merchant_user_ids:
                    await notif_service.notify_user(
                        user_id=uid,
                        title="طلب جديد",
                        message=f"لديك طلب جديد رقم #{created.id}.",
                        type="order",
                        data={"order_id": int(created.id), "store_id": store_id},
                        store_id=store_id,
                    )
    except Exception:
        pass

    return created

@router.get("/", response_model=List[Order])
async def list_orders(
    service: OrderService = Depends(get_order_service),
    current_user: AuthUser = Depends(get_current_user)
):
    return await service.get_customer_orders(current_user.id)


@router.get("/store", response_model=List[Order])
async def list_store_orders(
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_active_user),
    service: OrderService = Depends(get_order_service),
    store_id: int = Depends(require_current_store_id),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    return await service.order_repo.get_multi()

@router.get("/me/pending-count", response_model=PendingOrdersCount)
async def get_my_pending_orders_count(
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_active_user),
    store_id: int = Depends(require_current_store_id),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    count_result = await db.execute(
        select(func.count(OrderModel.id)).where(
            OrderModel.store_id == store_id,
            OrderModel.status == OrderStatus.PENDING,
        )
    )
    pending_orders = int(count_result.scalar() or 0)
    return PendingOrdersCount(pending_orders=pending_orders)

@router.post("/{order_id:int}/assign-courier", response_model=Order)
async def assign_courier_to_order(
    order_id: int,
    payload: AssignCourierRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_active_user),
    service: OrderService = Depends(get_order_service),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    result = await db.execute(select(StoreUser.store_id).where(StoreUser.user_id == current_user.id))
    store_id = result.scalar_one_or_none()
    if not store_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No store associated with this user")

    order = await service.order_repo.get_with_items(order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if getattr(order, "store_id", None) != store_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Order does not belong to your store")

    courier_result = await db.execute(
        select(CourierModel).where(
            CourierModel.user_id == payload.courier_user_id,
            CourierModel.store_id == store_id,
            CourierModel.status == CourierStatus.ACTIVE,
        )
    )
    courier = courier_result.scalar_one_or_none()
    if not courier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Courier not found or not active for this store")

    updated = await service.order_repo.update(order, {"courier_id": payload.courier_user_id})
    return await service.order_repo.get_with_items(updated.id)

@router.get("/{order_id:int}", response_model=Order)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_active_user),
    service: OrderService = Depends(get_order_service),
):
    order = await service.order_repo.get_with_items(order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Customer can only access their own orders
    if current_user.role == UserRole.CUSTOMER:
        if getattr(order, "customer_id", None) != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
        return order

    # Store roles can only access their store orders
    if current_user.role in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        store_id = await _resolve_store_id(db, current_user)
        if current_user.role != UserRole.SUPER_ADMIN and getattr(order, "store_id", None) != store_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Order does not belong to your store")
        return order

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

@router.patch("/{order_id:int}/status", response_model=Order)
async def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    service: OrderService = Depends(get_order_service),
    current_user: AuthUser = Depends(get_current_active_user)
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    return await service.update_status(order_id, status_update, current_user.id)


@router.post("/{order_id:int}/returns", response_model=ReturnRequest)
async def create_return_request(
    order_id: int,
    payload: ReturnRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_active_user),
):
    order_repo = OrderRepository(db)
    returns_repo = ReturnRequestRepository(db)

    order = await order_repo.get_with_items(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.customer_id != current_user.id and current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Not allowed")

    if order.status != OrderStatus.DELIVERED:
        raise HTTPException(status_code=400, detail="Return requests allowed only for delivered orders")

    existing = await db.execute(select(returns_repo.model).where(returns_repo.model.order_id == order_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Return request already exists for this order")

    rr = await returns_repo.create(
        {
            "store_id": order.store_id,
            "order_id": order.id,
            "customer_id": order.customer_id,
            "reason": payload.reason,
            "notes": payload.notes,
            "status": ReturnStatus.PENDING,
        }
    )
    await db.commit()
    await db.refresh(rr)
    rr_full = await returns_repo.get_with_images(rr.id)

    try:
        store_id = int(getattr(order, "store_id", None) or 0)
        if store_id:
            result = await db.execute(
                select(StoreUser.user_id)
                .where(StoreUser.store_id == store_id)
                .where(StoreUser.role.in_([UserRole.STORE_OWNER, UserRole.STORE_ADMIN]))
            )
            merchant_user_ids = list({int(x) for x in result.scalars().all() if x is not None})
            if merchant_user_ids:
                notif_service = NotificationService(NotificationRepository(db))
                for uid in merchant_user_ids:
                    await notif_service.notify_user(
                        user_id=uid,
                        title="طلب مرتجع جديد",
                        message=f"لديك طلب مرتجع جديد للطلب رقم #{order.id}.",
                        type="return",
                        data={"return_request_id": int(rr.id), "order_id": int(order.id), "store_id": store_id},
                        store_id=store_id,
                    )
    except Exception:
        pass

    return rr_full or rr


@router.post("/returns/{return_request_id}/proof/upload", response_model=ReturnRequest)
async def upload_return_proof_image(
    return_request_id: int,
    request: Request,
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_active_user),
):
    returns_repo = ReturnRequestRepository(db)
    proof_repo = ReturnProofImageRepository(db)

    rr = await returns_repo.get_with_images(return_request_id)
    if not rr:
        raise HTTPException(status_code=404, detail="Return request not found")

    # Owner customer or admin
    if rr.customer_id != current_user.id and current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Not allowed")

    suffix = Path(image.filename or "").suffix.lower()
    if suffix not in [".png", ".jpg", ".jpeg", ".webp"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    content = await image.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")

    uploads_dir = Path(__file__).resolve().parents[4] / "uploads" / "returns" / str(return_request_id)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}{suffix}"
    dest = uploads_dir / safe_name
    dest.write_bytes(content)

    base = str(request.base_url).rstrip("/")
    image_url = f"{base}/uploads/returns/{return_request_id}/{safe_name}"

    await proof_repo.create({"return_request_id": rr.id, "image_url": image_url})
    await db.commit()
    updated = await returns_repo.get_with_images(rr.id)
    return updated or rr


@router.get("/my/returns", response_model=List[ReturnRequest])
async def list_my_returns(
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_active_user),
):
    result = await db.execute(
        select(ReturnRequestModel)
        .options(selectinload(ReturnRequestModel.proof_images))
        .where(ReturnRequestModel.customer_id == current_user.id)
        .order_by(ReturnRequestModel.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/returns", response_model=List[ReturnRequest])
async def list_store_returns(
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_active_user),
    store_id: int = Depends(require_current_store_id),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")
    result = await db.execute(
        select(ReturnRequestModel).options(selectinload(ReturnRequestModel.proof_images))
        .where(ReturnRequestModel.store_id == store_id)
        .order_by(ReturnRequestModel.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/returns/{return_request_id}/approve", response_model=ReturnRequest)
async def approve_return_request(
    return_request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_active_user),
    store_id: int = Depends(require_current_store_id),
):
    payload = ReturnRequestReview(status=ReturnStatus.APPROVED)
    return await review_return_request(return_request_id, payload, db, current_user, store_id)


@router.post("/returns/{return_request_id}/reject", response_model=ReturnRequest)
async def reject_return_request(
    return_request_id: int,
    payload: ReturnRequestBase,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_active_user),
    store_id: int = Depends(require_current_store_id),
):
    review_payload = ReturnRequestReview(status=ReturnStatus.REJECTED, notes=payload.notes)
    return await review_return_request(return_request_id, review_payload, db, current_user, store_id)


@router.put("/returns/{return_request_id}/review", response_model=ReturnRequest)
async def review_return_request(
    return_request_id: int,
    payload: ReturnRequestReview,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_active_user),
    store_id: int = Depends(require_current_store_id),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    returns_repo = ReturnRequestRepository(db)
    order_repo = OrderRepository(db)
    history_repo = OrderHistoryRepository(db)

    rr = await returns_repo.get_with_images(return_request_id)
    if not rr:
        raise HTTPException(status_code=404, detail="Return request not found")

    if current_user.role != UserRole.SUPER_ADMIN and rr.store_id != store_id:
        raise HTTPException(status_code=403, detail="Return request does not belong to your store")

    if rr.status != ReturnStatus.PENDING:
        raise HTTPException(status_code=400, detail="Return request already reviewed")

    rr.status = payload.status
    rr.reviewed_by_id = current_user.id
    rr.reviewed_at = datetime.utcnow()
    if payload.notes:
        rr.notes = payload.notes
    db.add(rr)

    # On approval: restock inventory and update order status
    if payload.status == ReturnStatus.APPROVED:
        order = await order_repo.get_with_items(rr.order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        for item in order.items:
            inv_res = await db.execute(
                select(InventoryModel).where(
                    InventoryModel.product_id == item.product_id,
                    InventoryModel.store_id == order.store_id,
                )
            )
            inv = inv_res.scalar_one_or_none()
            if inv:
                inv.quantity = int(inv.quantity or 0) + int(item.quantity or 0)
                db.add(inv)
            else:
                db.add(
                    InventoryModel(
                        product_id=item.product_id,
                        store_id=order.store_id,
                        quantity=int(item.quantity or 0),
                        low_stock_threshold=5,
                    )
                )

        old_status = order.status
        order.status = OrderStatus.RETURNED
        db.add(order)

        await history_repo.create(
            {
                "order_id": order.id,
                "status_from": old_status,
                "status_to": OrderStatus.RETURNED,
                "changed_by_id": current_user.id,
                "note": "Return approved",
            }
        )

    try:
        notif_service = NotificationService(NotificationRepository(db))
        title = "تم قبول المرتجع" if payload.status == ReturnStatus.APPROVED else "تم رفض المرتجع"
        msg = (
            f"تم قبول طلب الإرجاع الخاص بالطلب رقم #{rr.order_id}."
            if payload.status == ReturnStatus.APPROVED
            else f"تم رفض طلب الإرجاع الخاص بالطلب رقم #{rr.order_id}."
        )
        await notif_service.notify_user(
            user_id=int(rr.customer_id),
            title=title,
            message=msg,
            type="return",
            data={"return_request_id": int(rr.id), "order_id": int(rr.order_id), "status": str(payload.status)},
            store_id=int(rr.store_id) if getattr(rr, "store_id", None) else None,
        )
    except Exception:
        pass

    await db.commit()
    updated = await returns_repo.get_with_images(rr.id)
    return updated or rr
