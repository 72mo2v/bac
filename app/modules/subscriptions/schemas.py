from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from .models import SubscriptionStatus, InvoiceStatus

class SubscriptionPlanBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    duration_days: int = 30
    trial_days: int = 7
    limits: Optional[Dict[str, Any]] = None
    is_active: bool = True

class SubscriptionPlanCreate(SubscriptionPlanBase):
    pass

class SubscriptionPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    duration_days: Optional[int] = None
    trial_days: Optional[int] = None
    limits: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class SubscriptionPlanInDB(SubscriptionPlanBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SubscriptionBase(BaseModel):
    store_id: int
    plan_id: int
    status: SubscriptionStatus = SubscriptionStatus.TRIAL
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    trial_end_date: Optional[datetime] = None
    auto_renew: bool = True

class SubscriptionCreate(SubscriptionBase):
    pass

class SubscriptionInDB(SubscriptionBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Nested Info
    store: Optional[Dict[str, Any]] = None
    plan: Optional[SubscriptionPlanInDB] = None

    class Config:
        from_attributes = True

class InvoiceBase(BaseModel):
    subscription_id: int
    amount: Decimal
    due_date: datetime
    status: InvoiceStatus = InvoiceStatus.PENDING
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    notes: Optional[str] = None

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceInDB(InvoiceBase):
    id: int
    paid_at: Optional[datetime] = None
    created_at: datetime
    
    # Nested Info
    subscription: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
