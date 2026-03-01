from typing import Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.deps import get_current_super_admin
from app.modules.auth.schemas import User as UserSchema, UserUpdate
from app.modules.auth.models import User, UserAccessStatus
from app.modules.auth.repositories.user_repository import UserRepository
from app.modules.audit.repositories.audit_repository import AuditRepository

router = APIRouter()

@router.get("/", response_model=List[UserSchema])
async def list_users(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    role: Optional[str] = None,
    current_admin: User = Depends(get_current_super_admin)
) -> Any:
    """List all users with optional filtering (Super Admin only)."""
    user_repo = UserRepository(db)
    query = select(User).options(
        selectinload(User.admin_details),
        selectinload(User.addresses)
    ).offset(skip).limit(limit)
    if role:
        query = query.filter(User.role == role)
    
    result = await db.execute(query)
    users = result.scalars().all()
    return users


@router.get("/{user_id}", response_model=UserSchema)
async def get_user_details(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin),
) -> Any:
    user_repo = UserRepository(db)
    user = await user_repo.get_profile(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}/status")
async def update_user_status(
    user_id: int,
    is_active: bool,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin)
) -> Any:
    """Activate or Ban a user (Super Admin only)."""
    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)
    
    user = await user_repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_status = user.is_active
    user.is_active = is_active
    await db.commit()
    
    # Log the action
    await audit_repo.log_action(
        admin_id=current_admin.id,
        action="UPDATE_USER_STATUS",
        target_type="user",
        target_id=str(user_id),
        changes={"is_active": {"old": old_status, "new": is_active}},
        ip_address=request.client.host
    )
    
    return {"message": f"User status updated to {'active' if is_active else 'inactive'}"}


@router.put("/{user_id}/access")
async def update_user_access(
    user_id: int,
    access_status: UserAccessStatus,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin),
    reason: Optional[str] = None,
    suspended_until: Optional[datetime] = None,
) -> Any:
    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)

    user = await user_repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old = {
        "access_status": user.access_status,
        "access_reason": user.access_reason,
        "suspended_until": user.suspended_until,
    }

    user.access_status = access_status
    user.access_reason = reason
    user.suspended_until = suspended_until

    # If user is marked BLOCKED/SUSPENDED, make sure legacy flag is false too.
    if access_status in [UserAccessStatus.BLOCKED, UserAccessStatus.SUSPENDED]:
        user.is_active = False
    else:
        user.is_active = True

    await db.commit()

    await audit_repo.log_action(
        admin_id=current_admin.id,
        action="UPDATE_USER_ACCESS",
        target_type="user",
        target_id=str(user_id),
        changes={
            "access_status": {"old": str(old["access_status"]), "new": str(access_status)},
            "access_reason": {"old": old["access_reason"], "new": reason},
            "suspended_until": {
                "old": old["suspended_until"].isoformat() if old["suspended_until"] else None,
                "new": suspended_until.isoformat() if suspended_until else None,
            },
        },
        ip_address=request.client.host,
    )

    return {"message": "User access updated"}

@router.put("/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin)
) -> Any:
    """Update user details (Super Admin only)."""
    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)
    
    query = select(User).options(
        selectinload(User.admin_details),
        selectinload(User.addresses)
    ).filter(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    updated_user = await user_repo.update(db_obj=user, obj_in=user_in.model_dump(exclude_unset=True))
    
    # Log the action
    await audit_repo.log_action(
        admin_id=current_admin.id,
        action="UPDATE_USER_DETAILS",
        target_type="user",
        target_id=str(user_id),
        changes={"full_name": user_in.full_name, "email": user_in.email},
        ip_address=request.client.host
    )
    
    return updated_user

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin)
) -> Any:
    """Delete a user permanently (Super Admin only)."""
    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)
    
    user = await user_repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
        
    await user_repo.remove(id=user_id)
    
    # Log the action
    await audit_repo.log_action(
        admin_id=current_admin.id,
        action="DELETE_USER",
        target_type="user",
        target_id=str(user_id),
        changes={"deleted": user.full_name},
        ip_address=request.client.host
    )
    
    return {"message": "User deleted successfully"}

