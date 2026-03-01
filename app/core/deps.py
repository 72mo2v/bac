from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.config import settings
from app.core.database import get_db
from app.core.security import ALGORITHM
from datetime import datetime, timezone
from app.modules.auth.models import User, UserRole, UserAccessStatus
from app.modules.auth.repositories.user_repository import UserRepository
from app.core.middleware import get_store_id, set_store_id
from sqlalchemy import select
from app.modules.rbac.services.rbac_service import RBACService
from app.modules.auth.models import StoreUser

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    query = select(User).options(
        selectinload(User.admin_details),
        selectinload(User.addresses)
    ).filter(User.id == int(user_id))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    if current_user.access_status == UserAccessStatus.BLOCKED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ACCOUNT_BLOCKED",
                "message": current_user.access_reason or "Account is blocked",
            },
        )

    if current_user.access_status == UserAccessStatus.SUSPENDED:
        until = current_user.suspended_until
        now = datetime.now(timezone.utc)
        if until is None or until > now:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "ACCOUNT_SUSPENDED",
                    "message": current_user.access_reason or "Account is suspended",
                    "suspended_until": until.isoformat() if until else None,
                },
            )
    return current_user

async def get_current_admin(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Check if user has any admin role in RBAC system"""
    rbac_service = RBACService(db)
    admin_user = await rbac_service.admin_user_repo.get_by_user_id(current_user.id)
    
    # Fallback to legacy check if SUPER_ADMIN directly
    if current_user.role == UserRole.SUPER_ADMIN or admin_user:
        return current_user
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="The user doesn't have administrative privileges"
    )

async def get_current_super_admin(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Check if user is a top-level SUPER_ADMIN"""
    rbac_service = RBACService(db)
    is_super = await rbac_service.is_super_admin(current_user.id)
    
    if is_super or current_user.role == UserRole.SUPER_ADMIN:
        return current_user
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="The user doesn't have enough privileges"
    )

class PermissionChecker:
    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        # Full SUPER_ADMIN bypasses all checks
        if current_user.role == UserRole.SUPER_ADMIN:
            return current_user
            
        rbac_service = RBACService(db)
        is_super = await rbac_service.is_super_admin(current_user.id)
        if is_super:
            return current_user
            
        permissions = await rbac_service.get_user_permissions(current_user.id)
        if self.required_permission in permissions:
            return current_user
            
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required permission: {self.required_permission}"
        )

async def check_subscription(
    db: AsyncSession = Depends(get_db)
) -> None:
    from app.modules.subscriptions.models import Subscription, SubscriptionStatus
    store_id = get_store_id()
    if not store_id:
        return
    
    query = select(Subscription).filter(Subscription.store_id == store_id)
    result = await db.execute(query)
    sub = result.scalar_one_or_none()
    
    if not sub or sub.status not in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required"
        )


async def require_current_store_id(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> int:
    """Resolve store_id from authenticated user's membership and set it into request context.

    This prevents trusting client-provided headers like X-Store-ID.
    """
    # If a store context was provided (e.g. X-Store-Id), validate membership and use it.
    ctx_store_id = get_store_id()
    if ctx_store_id:
        if current_user.role == UserRole.SUPER_ADMIN:
            set_store_id(int(ctx_store_id))
            return int(ctx_store_id)

        membership = await db.execute(
            select(StoreUser.id).where(
                StoreUser.user_id == current_user.id,
                StoreUser.store_id == int(ctx_store_id),
            )
        )
        if membership.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Store access denied")

        set_store_id(int(ctx_store_id))
        return int(ctx_store_id)

    result = await db.execute(
        select(StoreUser.store_id).where(StoreUser.user_id == current_user.id).order_by(StoreUser.store_id.asc())
    )
    store_id = result.scalars().first()
    if not store_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No store associated with this user")

    set_store_id(int(store_id))
    return int(store_id)
