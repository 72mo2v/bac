from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from app.modules.payments.models import PaymentMethod, PaymentStatus


class PaymentCustomerMinimal(BaseModel):
    id: int
    full_name: Optional[str] = None

    class Config:
        from_attributes = True


class PaymentOrderMinimal(BaseModel):
    id: int
    customer: Optional[PaymentCustomerMinimal] = None

    class Config:
        from_attributes = True

class StorePaymentMethodBase(BaseModel):
    method_type: PaymentMethod
    display_name: str
    details: Optional[dict] = None
    instructions: Optional[str] = None
    is_enabled: bool = True

class StorePaymentMethodCreate(StorePaymentMethodBase):
    pass

class StorePaymentMethodUpdate(BaseModel):
    display_name: Optional[str] = None
    details: Optional[dict] = None
    instructions: Optional[str] = None
    is_enabled: Optional[bool] = None

class StorePaymentMethod(StorePaymentMethodBase):
    id: int
    store_id: int
    
    class Config:
        from_attributes = True

class PaymentBase(BaseModel):
    method: PaymentMethod
    store_payment_method_id: Optional[int] = None
    transaction_reference: Optional[str] = None
    proof_image_url: Optional[str] = None

class PaymentCreate(PaymentBase):
    order_id: int

class PaymentUpdate(BaseModel):
    status: Optional[PaymentStatus] = None
    admin_notes: Optional[str] = None

class Payment(PaymentBase):
    id: int
    order_id: int
    store_id: int
    amount: float
    status: PaymentStatus
    created_at: datetime
    store_payment_method: Optional[StorePaymentMethod] = None
    order: Optional[PaymentOrderMinimal] = None
    
    class Config:
        from_attributes = True
