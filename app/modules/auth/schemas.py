from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from app.modules.auth.models import UserRole, UserAccessStatus

# Address Schemas
class AddressBase(BaseModel):
    title: str
    full_address: str
    city: str
    country: str = "Egypt"
    phone: Optional[str] = None
    is_default: bool = False

class AddressCreate(AddressBase):
    pass

class AddressUpdate(BaseModel):
    title: Optional[str] = None
    full_address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    is_default: Optional[bool] = None

class Address(AddressBase):
    id: int
    user_id: int
    class Config:
        from_attributes = True

# Shared properties
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    access_status: Optional[UserAccessStatus] = UserAccessStatus.ACTIVE
    access_reason: Optional[str] = None
    suspended_until: Optional[datetime] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    avatar_url: Optional[str] = None
    nationality: Optional[str] = None
    id_card_url: Optional[str] = None
    store_front_photo_url: Optional[str] = None
    role: Optional[UserRole] = UserRole.CUSTOMER
    admin_role_id: Optional[int] = None

# Properties to receive via API on creation
class UserCreate(UserBase):
    email: EmailStr
    password: str = Field(..., min_length=8)

# Properties to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = None
    admin_role_id: Optional[int] = None

class UserInDBBase(UserBase):
    id: Optional[int] = None
    is_verified: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Additional properties to return via API
class User(UserInDBBase):
    addresses: List[Address] = []

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str

class TokenPayload(BaseModel):
    sub: Optional[int] = None
    role: Optional[str] = None
    store_id: Optional[int] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    app: Optional[str] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class UserSession(BaseModel):
    id: str
    device_type: Optional[str] = None
    device_name: Optional[str] = None
    ip_address: Optional[str] = None
    last_active: Optional[datetime] = None
    is_current: bool = False

    class Config:
        from_attributes = True
