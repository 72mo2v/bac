from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Table, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

# Many-to-Many relationship between AdminRoles and Permissions
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('admin_roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True)
)

class Permission(Base):
    """Individual permissions that can be assigned to roles"""
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # e.g., "users.create", "orders.view"
    display_name = Column(String, nullable=False)  # e.g., "إنشاء مستخدمين"
    description = Column(Text, nullable=True)
    category = Column(String, nullable=False)  # e.g., "users", "orders", "products"
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    roles = relationship("AdminRole", secondary=role_permissions, back_populates="permissions")

class AdminRole(Base):
    """Admin roles with customizable permissions"""
    __tablename__ = "admin_roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # e.g., "SUPER_ADMIN", "SUPER_ADMIN_2"
    display_name = Column(String, nullable=False)  # e.g., "مدير عام", "مدير مساعد"
    description = Column(Text, nullable=True)
    is_system_role = Column(Boolean, default=False)  # True for SUPER_ADMIN (cannot be deleted/modified)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
    users = relationship("AdminUser", back_populates="role")

class AdminUser(Base):
    """Admin users with role-based permissions"""
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    role_id = Column(Integer, ForeignKey("admin_roles.id"), nullable=False)
    
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("app.modules.auth.models.User", foreign_keys=[user_id], back_populates="admin_details")
    role = relationship("AdminRole", back_populates="users")
    creator = relationship("app.modules.auth.models.User", foreign_keys=[created_by])
