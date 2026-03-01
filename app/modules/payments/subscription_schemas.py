from typing import Optional, Any, Dict, List
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from decimal import Decimal

class SubscriptionPaymentMethodBase(BaseModel):
    name: str
    provider: str
    is_enabled: bool = True
    display_order: int = 0
    config: Dict[str, Any]

class SubscriptionPaymentMethodCreate(SubscriptionPaymentMethodBase):
    pass

class SubscriptionPaymentMethodUpdate(BaseModel):
    name: Optional[str] = None
    is_enabled: Optional[bool] = None
    display_order: Optional[int] = None
    config: Optional[Dict[str, Any]] = None

class SubscriptionPaymentMethod(SubscriptionPaymentMethodBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# --- Payments ---

class SubscriptionPaymentInitiate(BaseModel):
    plan_id: int
    method_id: int
    success_url: str
    cancel_url: str

class SubscriptionPaymentBase(BaseModel):
    amount: Decimal
    currency: str = "EGP"
    status: str
    paid_at: Optional[datetime] = None

class SubscriptionPayment(SubscriptionPaymentBase):
    id: int
    store_id: int
    subscription_id: Optional[int] = None
    invoice_id: Optional[int] = None
    payment_method_id: int
    method: Optional[SubscriptionPaymentMethod] = None
    transaction_id: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
