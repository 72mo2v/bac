from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, Table, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base
import uuid

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    STORE_OWNER = "STORE_OWNER"
    STORE_ADMIN = "STORE_ADMIN"
    COURIER = "COURIER"
    CUSTOMER = "CUSTOMER"

class UserAccessStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    SUSPENDED = "SUSPENDED"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    phone_number = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    nationality = Column(String, nullable=True)
    id_card_url = Column(String, nullable=True)
    store_front_photo_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    access_status = Column(Enum(UserAccessStatus), default=UserAccessStatus.ACTIVE)
    access_reason = Column(Text, nullable=True)
    suspended_until = Column(DateTime(timezone=True), nullable=True)
    is_verified = Column(Boolean, default=False)
    role = Column(Enum(UserRole), default=UserRole.CUSTOMER)
    
    # Audit timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relations
    addresses = relationship("Address", back_populates="user", cascade="all, delete-orphan")

    # Multi-tenancy relations
    store_memberships = relationship("StoreUser", back_populates="user")
    admin_details = relationship(
        "AdminUser", 
        back_populates="user", 
        uselist=False,
        foreign_keys="AdminUser.user_id"
    )

    @property
    def admin_role_id(self) -> Optional[int]:
        if self.admin_details:
            return self.admin_details.role_id
        return None

class StoreUser(Base):
    """Link between Users and Stores for Multi-Tenancy"""
    __tablename__ = "store_users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    store_id = Column(Integer, index=True) # Linked to Store model in another module
    role = Column(Enum(UserRole), default=UserRole.STORE_ADMIN)

    user = relationship("User", back_populates="store_memberships")

class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False) # e.g., "Home", "Work"
    full_address = Column(Text, nullable=False)
    city = Column(String, nullable=False)
    country = Column(String, default="Egypt")
    phone = Column(String, nullable=True)
    is_default = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="addresses")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device_type = Column(String, nullable=True)
    device_name = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    last_active = Column(DateTime(timezone=True), server_default=func.now())
    is_current = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
