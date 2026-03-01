from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.rbac.repositories.rbac_repository import PermissionRepository, AdminRoleRepository, AdminUserRepository
from app.modules.rbac.models import AdminRole, AdminUser, Permission
from app.modules.rbac.schemas import AdminRoleCreate, AdminRoleUpdate, AdminUserCreate
from fastapi import HTTPException, status

class RBACService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.permission_repo = PermissionRepository(db)
        self.role_repo = AdminRoleRepository(db)
        self.admin_user_repo = AdminUserRepository(db)

    # --- Role Management ---
    async def create_role(self, role_in: AdminRoleCreate) -> AdminRole:
        # Check if role name already exists
        # Basic implementation, can be expanded
        role_dict = role_in.model_dump(exclude={"permission_ids"})
        role = await self.role_repo.create(role_dict)
        
        if role_in.permission_ids:
            await self.update_role_permissions(role.id, role_in.permission_ids)
            
        return await self.role_repo.get_with_permissions(role.id)

    async def update_role(self, role_id: int, role_in: AdminRoleUpdate) -> AdminRole:
        role = await self.role_repo.get(role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        
        if role.is_system_role and (role_in.display_name or role_in.is_active is not None):
             # System roles are partially protected
             pass

        update_data = role_in.model_dump(exclude={"permission_ids"}, exclude_unset=True)
        await self.role_repo.update(role, update_data)
        
        if role_in.permission_ids is not None:
            await self.update_role_permissions(role_id, role_in.permission_ids)
            
        return await self.role_repo.get_with_permissions(role_id)

    async def update_role_permissions(self, role_id: int, permission_ids: List[int]):
        role = await self.role_repo.get_with_permissions(role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        
        # Clear existing permissions and add new ones
        # This is a simple implementation for many-to-many update
        role.permissions = []
        for p_id in permission_ids:
            perm = await self.permission_repo.get(p_id)
            if perm:
                role.permissions.append(perm)
        
        await self.db.commit()

    # --- Admin User Management ---
    async def assign_role_to_user(self, admin_in: AdminUserCreate, creator_id: int) -> AdminUser:
        # Check if user already has an admin role
        existing = await self.admin_user_repo.get_by_user_id(admin_in.user_id)
        if existing:
            # Update role instead of creating new
            return await self.admin_user_repo.update(existing, {"role_id": admin_in.role_id})
        
        admin_dict = admin_in.model_dump()
        admin_dict["created_by"] = creator_id
        return await self.admin_user_repo.create(admin_dict)

    async def get_user_permissions(self, user_id: int) -> List[str]:
        admin_user = await self.admin_user_repo.get_by_user_id(user_id)
        if not admin_user or not admin_user.is_active:
            return []
        
        if not admin_user.role or not admin_user.role.is_active:
            return []
            
        return [p.name for p in admin_user.role.permissions]

    async def is_super_admin(self, user_id: int) -> bool:
        admin_user = await self.admin_user_repo.get_by_user_id(user_id)
        return admin_user and admin_user.role.name == "SUPER_ADMIN"
