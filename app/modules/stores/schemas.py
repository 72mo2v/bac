from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime
from app.modules.stores.models import StoreVerificationStatus
from app.modules.auth.models import UserRole

class StoreBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    working_hours: Optional[str] = None
    return_policy: Optional[str] = None
    is_active: Optional[bool] = True

    min_order_total: Optional[float] = None
    order_shipping_fee: Optional[float] = None


class StoreCreate(StoreBase):
    pass

class StoreUpdate(StoreBase):
    name: Optional[str] = None
    slug: Optional[str] = None

class StoreInDBBase(StoreBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    logo_url: Optional[str] = None
    verification_status: Optional[StoreVerificationStatus] = None
    is_verified: Optional[bool] = None
    commercial_registration_url: Optional[str] = None
    id_card_url: Optional[str] = None
    store_front_photo_url: Optional[str] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    verification_notes: Optional[str] = None
    verified_at: Optional[datetime] = None
    verified_by_id: Optional[int] = None

    class Config:
        from_attributes = True

class Store(StoreInDBBase):
    pass


class StoreOwnerOut(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None

    class Config:
        from_attributes = True


class AdminStore(StoreInDBBase):
    owner: Optional[StoreOwnerOut] = None


class StoreMembership(BaseModel):
    store: Store
    role: UserRole

    class Config:
        from_attributes = True


class StoreVerificationSubmit(BaseModel):
    commercial_registration_url: Optional[str] = None
    id_card_url: Optional[str] = None
    store_front_photo_url: Optional[str] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None


class StoreVerificationAdminReview(BaseModel):
    status: StoreVerificationStatus
    verification_notes: Optional[str] = None


class StoreDashboardStatsToday(BaseModel):
    orders_count: int
    revenue: float


class StoreDashboardStatsCurrent(BaseModel):
    active_products: int
    low_stock_products: int
    pending_orders: int
    active_couriers: int
    busy_couriers: int


class StoreDashboardStats(BaseModel):
    today: StoreDashboardStatsToday
    current: StoreDashboardStatsCurrent
    subscription_status: Optional[str] = None
    subscription_days_left: Optional[int] = None
