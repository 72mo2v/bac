from typing import Optional
from pydantic import BaseModel, Field
from pydantic import EmailStr
from datetime import datetime
from app.modules.couriers.models import CourierStatus

class CourierBase(BaseModel):
    vehicle_type: str
    license_plate: str
    store_id: Optional[int] = None
    courier_code: Optional[str] = None

class CourierCreate(CourierBase):
    user_id: int
    status: Optional[CourierStatus] = CourierStatus.PENDING


class CourierAccountCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    vehicle_type: str
    license_plate: str


class CourierUpdate(BaseModel):
    status: Optional[CourierStatus] = None
    is_available: Optional[bool] = None
    vehicle_type: Optional[str] = None
    license_plate: Optional[str] = None
    courier_code: Optional[str] = None

    class Config:
        from_attributes = True


class CourierUserMinimal(BaseModel):
    id: int
    email: Optional[str] = None
    full_name: Optional[str] = None

    class Config:
        from_attributes = True


class Courier(CourierBase):
    id: int
    user_id: int
    status: CourierStatus
    is_available: bool
    created_at: datetime
    user: Optional[CourierUserMinimal] = None
    
    class Config:
        from_attributes = True
