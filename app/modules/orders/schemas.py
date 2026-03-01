from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from app.modules.orders.models import OrderStatus, ReturnStatus
from app.modules.stores.schemas import Store


class OrderCustomerMinimal(BaseModel):
    id: int
    full_name: Optional[str] = None

    class Config:
        from_attributes = True

class OrderItemBase(BaseModel):
    product_id: int
    quantity: int

class OrderItemCreate(OrderItemBase):
    pass

class ProductOrderItem(BaseModel):
    id: int
    name: str
    image_url: Optional[str] = None
    price: float
    
    class Config:
        from_attributes = True

class OrderItem(OrderItemBase):
    id: int
    unit_price: float
    total_price: float
    product: Optional[ProductOrderItem] = None
    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    shipping_address: str

class OrderCreate(OrderBase):
    store_id: int  # Required at creation
    items: List[OrderItemCreate]

class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    courier_id: Optional[int] = None

class Order(OrderBase):
    id: int
    store_id: int
    customer_id: int
    customer: Optional[OrderCustomerMinimal] = None
    courier_id: Optional[int] = None
    status: OrderStatus
    total_amount: float
    is_paid: bool
    created_at: datetime
    items: List[OrderItem]
    store: Optional[Store] = None
    delivery_qr_code: Optional[str] = None
    
    class Config:
        from_attributes = True

class OrderStatusUpdate(BaseModel):
    new_status: OrderStatus
    note: Optional[str] = None


class PendingOrdersCount(BaseModel):
    pending_orders: int


class AssignCourierRequest(BaseModel):
    courier_user_id: int


class ReturnProofImage(BaseModel):
    id: int
    image_url: str
    created_at: datetime

    class Config:
        from_attributes = True


class ReturnRequestBase(BaseModel):
    reason: Optional[str] = None
    notes: Optional[str] = None


class ReturnRequestCreate(ReturnRequestBase):
    pass


class ReturnRequestReview(BaseModel):
    status: ReturnStatus
    notes: Optional[str] = None


class ReturnRequest(ReturnRequestBase):
    id: int
    store_id: int
    order_id: int
    customer_id: int
    status: ReturnStatus
    reviewed_by_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    proof_images: List[ReturnProofImage] = []

    class Config:
        from_attributes = True
