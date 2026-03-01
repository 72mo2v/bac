from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.base_repository import BaseRepository
from app.modules.rbac.models import Permission, AdminRole, AdminUser

class PermissionRepository(BaseRepository[Permission]):
    def __init__(self, db):
        super().__init__(Permission, db)
    
    async def get_by_category(self, category: str) -> List[Permission]:
        query = select(Permission).filter(Permission.category == category)
        result = await self.db.execute(query)
        return list(result.scalars().all())

class AdminRoleRepository(BaseRepository[AdminRole]):
    def __init__(self, db):
        super().__init__(AdminRole, db)
    
    async def get_with_permissions(self, role_id: int) -> Optional[AdminRole]:
        query = select(AdminRole).options(
            selectinload(AdminRole.permissions)
        ).filter(AdminRole.id == role_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all_with_permissions(self) -> List[AdminRole]:
        query = select(AdminRole).options(
            selectinload(AdminRole.permissions)
        ).order_by(AdminRole.is_system_role.desc(), AdminRole.name)
        result = await self.db.execute(query)
        return list(result.scalars().all())

class AdminUserRepository(BaseRepository[AdminUser]):
    def __init__(self, db):
        super().__init__(AdminUser, db)
    
    async def get_by_user_id(self, user_id: int) -> Optional[AdminUser]:
        query = select(AdminUser).options(
            selectinload(AdminUser.role).selectinload(AdminRole.permissions)
        ).filter(AdminUser.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all_with_details(self) -> List[AdminUser]:
        query = select(AdminUser).options(
            selectinload(AdminUser.user),
            selectinload(AdminUser.role).selectinload(AdminRole.permissions)
        ).order_by(AdminUser.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())
