from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

# Permission Schemas
class PermissionBase(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    category: str

class PermissionCreate(PermissionBase):
    pass

class Permission(PermissionBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# AdminRole Schemas
class AdminRoleBase(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    is_active: bool = True

class AdminRoleCreate(AdminRoleBase):
    permission_ids: List[int] = []

class AdminRoleUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    permission_ids: Optional[List[int]] = None

class AdminRole(AdminRoleBase):
    id: int
    is_system_role: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    permissions: List[Permission] = []
    
    class Config:
        from_attributes = True

# AdminUser Schemas
class AdminUserBase(BaseModel):
    user_id: int
    role_id: int

class AdminUserCreate(AdminUserBase):
    pass

class AdminUserUpdate(BaseModel):
    role_id: Optional[int] = None
    is_active: Optional[bool] = None

class AdminUserDetail(BaseModel):
    id: int
    user_id: int
    role_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    user: dict  # Will contain user info
    role: AdminRole
    
    class Config:
        from_attributes = True
