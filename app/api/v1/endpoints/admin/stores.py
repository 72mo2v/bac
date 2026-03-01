from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_super_admin
from app.modules.stores.schemas import Store, StoreVerificationAdminReview, AdminStore, StoreOwnerOut
from app.modules.stores.models import StoreVerificationStatus
from datetime import datetime
from app.modules.stores.repositories.store_repository import StoreRepository
from app.modules.audit.repositories.audit_repository import AuditRepository
from app.modules.auth.models import User, UserRole, StoreUser
from app.modules.notifications.repositories.notification_repository import NotificationRepository
from app.modules.notifications.services.notification_service import NotificationService

router = APIRouter()


async def _get_store_owner(db: AsyncSession, store_id: int) -> Optional[User]:
    result = await db.execute(
        select(User)
        .join(StoreUser, StoreUser.user_id == User.id)
        .where(StoreUser.store_id == store_id)
        .where(StoreUser.role == UserRole.STORE_OWNER)
        .limit(1)
    )
    return result.scalar_one_or_none()


def _admin_store_out(store_obj, owner_obj: Optional[User]) -> AdminStore:
    store_out = AdminStore.model_validate(store_obj)
    if owner_obj:
        store_out = AdminStore.model_validate({
            **store_out.model_dump(),
            "owner": StoreOwnerOut.model_validate(owner_obj),
        })
    return store_out


@router.get("/verification-requests", response_model=List[AdminStore])
async def list_verification_requests(
    db: AsyncSession = Depends(get_db),
    days_overdue: Optional[int] = Query(default=None, ge=1),
    current_admin: User = Depends(get_current_super_admin),
):
    store_repo = StoreRepository(db)
    stores = await store_repo.get_multi(skip=0, limit=1000)

    # Show stores submitted for review and still not approved/rejected
    pending = [
        s
        for s in stores
        if getattr(s, "is_active", True)
        and getattr(s, "verification_status", None) == StoreVerificationStatus.UNDER_REVIEW
    ]

    if days_overdue is not None:
        threshold = datetime.utcnow().timestamp() - (days_overdue * 86400)
        pending = [
            s
            for s in pending
            if getattr(s, "updated_at", None) is not None and s.updated_at.timestamp() <= threshold
        ]

    pending.sort(key=lambda s: getattr(s, "updated_at", getattr(s, "created_at", None)) or datetime.utcnow(), reverse=True)

    out: List[AdminStore] = []
    for s in pending:
        owner = await _get_store_owner(db, int(s.id))
        out.append(_admin_store_out(s, owner))

    return out


@router.get("/{store_id}", response_model=AdminStore)
async def get_store_details(
    store_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin),
):
    store_repo = StoreRepository(db)
    store = await store_repo.get(store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    owner = await _get_store_owner(db, int(store.id))
    return _admin_store_out(store, owner)

@router.get("/", response_model=List[Store])
async def list_stores(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    current_admin: User = Depends(get_current_super_admin)
) -> Any:
    """List all stores with optional filtering (Super Admin only)."""
    store_repo = StoreRepository(db)
    stores = await store_repo.get_multi(skip=skip, limit=limit)
    if is_active is not None:
        stores = [s for s in stores if s.is_active == is_active]
    return stores

@router.put("/{store_id}/status")
async def update_store_status(
    store_id: int,
    is_active: bool,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin)
) -> Any:
    """Approve or Disable a store (Super Admin only)."""
    store_repo = StoreRepository(db)
    audit_repo = AuditRepository(db)
    store = await store_repo.get(store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    
    old_status = store.is_active
    store.is_active = is_active
    await db.commit()
    
    # Log the action
    await audit_repo.log_action(
        admin_id=current_admin.id,
        action="UPDATE_STORE_STATUS",
        target_type="store",
        target_id=str(store_id),
        changes={"is_active": {"old": old_status, "new": is_active}},
        ip_address=request.client.host
    )
    
    return {"message": f"Store status updated to {'active' if is_active else 'inactive'}"}

@router.delete("/{store_id}")
async def delete_store(
    store_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin)
) -> Any:
    """Delete a store permanently (Super Admin only)."""
    store_repo = StoreRepository(db)
    audit_repo = AuditRepository(db)
    
    store = await store_repo.get(store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    
    await store_repo.remove(store_id)
    
    # Log the action
    await audit_repo.log_action(
        admin_id=current_admin.id,
        action="DELETE_STORE",
        target_type="store",
        target_id=str(store_id),
        changes={"deleted": store.name},
        ip_address=request.client.host
    )
    
    return {"message": "Store deleted successfully"}


@router.put("/{store_id}/verification", response_model=Store)
async def review_store_verification(
    store_id: int,
    payload: StoreVerificationAdminReview,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin),
):
    store_repo = StoreRepository(db)
    audit_repo = AuditRepository(db)
    notif_service = NotificationService(NotificationRepository(db))

    store = await store_repo.get(store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    owner = await _get_store_owner(db, int(store.id))

    old_status = getattr(store, "verification_status", None)
    old_verified = getattr(store, "is_verified", None)
    old_notes = getattr(store, "verification_notes", None)

    store.verification_status = payload.status
    store.verification_notes = payload.verification_notes

    if payload.status == StoreVerificationStatus.APPROVED:
        store.is_verified = True
        store.verified_at = datetime.utcnow()
        store.verified_by_id = current_admin.id
        store.is_active = True
    elif payload.status == StoreVerificationStatus.REJECTED:
        store.is_verified = False
        store.verified_by_id = current_admin.id
        store.is_active = False
    else:
        store.is_verified = False

    await db.commit()
    await db.refresh(store)

    # Notify merchant (store owner)
    if owner:
        if payload.status == StoreVerificationStatus.APPROVED:
            await notif_service.notify_user(
                user_id=owner.id,
                title="تم توثيق متجرك",
                message=f"تمت الموافقة على توثيق متجر {store.name}.",
                type="store_verification",
                data={"store_id": store.id, "status": "APPROVED"},
                store_id=store.id,
            )
        elif payload.status == StoreVerificationStatus.REJECTED:
            await notif_service.notify_user(
                user_id=owner.id,
                title="تم رفض توثيق متجرك",
                message=f"تم رفض توثيق متجر {store.name}. يمكنك إنشاء متجر جديد وإعادة التقديم.",
                type="store_verification",
                data={"store_id": store.id, "status": "REJECTED", "notes": payload.verification_notes},
                store_id=store.id,
            )
        else:
            await notif_service.notify_user(
                user_id=owner.id,
                title="مطلوب إعادة التحقق من متجرك",
                message=(payload.verification_notes or "برجاء تحديث بيانات ومتطلبات التوثيق ثم إعادة الإرسال."),
                type="store_verification",
                data={"store_id": store.id, "status": str(payload.status), "notes": payload.verification_notes},
                store_id=store.id,
            )

    await audit_repo.log_action(
        admin_id=current_admin.id,
        action="REVIEW_STORE_VERIFICATION",
        target_type="store",
        target_id=str(store_id),
        changes={
            "verification_status": {"old": str(old_status) if old_status else None, "new": str(payload.status)},
            "is_verified": {"old": old_verified, "new": store.is_verified},
            "verification_notes": {"old": old_notes, "new": payload.verification_notes},
        },
        ip_address=request.client.host,
    )

    return store

