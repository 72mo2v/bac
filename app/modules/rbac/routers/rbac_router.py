from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_super_admin
from app.modules.auth.schemas import User
from app.modules.rbac.services.rbac_service import RBACService
from app.modules.rbac.schemas import (
    Permission, AdminRole, AdminRoleCreate, AdminRoleUpdate,
    AdminUserCreate, AdminUserDetail
)
from app.modules.rbac.repositories.rbac_repository import PermissionRepository, AdminRoleRepository, AdminUserRepository

router = APIRouter()

@router.get("/permissions", response_model=List[Permission])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin)
):
    repo = PermissionRepository(db)
    return await repo.get_all()

@router.get("/roles", response_model=List[AdminRole])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin)
):
    repo = AdminRoleRepository(db)
    return await repo.get_all_with_permissions()

@router.post("/roles", response_model=AdminRole)
async def create_role(
    role_in: AdminRoleCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin)
):
    service = RBACService(db)
    return await service.create_role(role_in)

@router.put("/roles/{role_id}", response_model=AdminRole)
async def update_role(
    role_id: int,
    role_in: AdminRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin)
):
    service = RBACService(db)
    return await service.update_role(role_id, role_in)

@router.get("/admins", response_model=List[AdminUserDetail])
async def list_admin_users(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin)
):
    repo = AdminUserRepository(db)
    return await repo.get_all_with_details()

@router.post("/admins", response_model=Any)
async def assign_admin_role(
    admin_in: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin)
):
    service = RBACService(db)
    return await service.assign_role_to_user(admin_in, current_admin.id)
