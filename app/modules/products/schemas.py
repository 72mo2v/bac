from typing import Optional, List
from pydantic import BaseModel, model_validator
from datetime import datetime

# Category Schemas
class CategoryBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    display_order: int = 0
    icon_url: Optional[str] = None
    is_visible: bool = True

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase):
    id: int
    store_id: Optional[int]
    class Config:
        from_attributes = True


class CategoryReorderItem(BaseModel):
    id: int
    display_order: int


class CategoryReorderRequest(BaseModel):
    items: List[CategoryReorderItem]


class LowStockProduct(BaseModel):
    product_id: int
    name: str
    quantity: int
    low_stock_threshold: int
    image_url: Optional[str] = None

# Inventory Schemas
class InventoryBase(BaseModel):
    quantity: int = 0
    low_stock_threshold: int = 5

class InventoryUpdate(BaseModel):
    quantity: Optional[int] = None
    low_stock_threshold: Optional[int] = None

class Inventory(InventoryBase):
    product_id: int
    class Config:
        from_attributes = True

# Product Schemas
class ProductImageBase(BaseModel):
    image_url: str
    display_order: int = 0
    is_primary: bool = False


class ProductImage(ProductImageBase):
    id: int
    product_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    price: float
    compare_at_price: Optional[float] = None
    sku: Optional[str] = None
    image_url: Optional[str] = None
    is_deal: bool = False
    is_bestseller: bool = False
    is_featured: bool = False
    deal_price: Optional[float] = None
    deal_end_date: Optional[datetime] = None
    is_active: bool = True
    origin: Optional[str] = "LOCAL"
    is_free_shipping: bool = True
    shipping_fee: float = 0
    max_qty_per_order: Optional[int] = None
    category_id: Optional[int] = None
    store_id: Optional[int] = None

    @model_validator(mode="after")
    def _validate_shipping(self):
        if self.is_free_shipping:
            self.shipping_fee = 0
            return self

        if self.shipping_fee is None:
            raise ValueError("shipping_fee is required when is_free_shipping is false")
        if float(self.shipping_fee) < 0:
            raise ValueError("shipping_fee must be >= 0")
        return self

class ProductCreate(ProductBase):
    inventory: Optional[InventoryBase] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    compare_at_price: Optional[float] = None
    sku: Optional[str] = None
    image_url: Optional[str] = None
    is_deal: Optional[bool] = None
    is_bestseller: Optional[bool] = None
    is_featured: Optional[bool] = None
    deal_price: Optional[float] = None
    deal_end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    is_free_shipping: Optional[bool] = None
    shipping_fee: Optional[float] = None
    max_qty_per_order: Optional[int] = None
    category_id: Optional[int] = None

    @model_validator(mode="after")
    def _validate_shipping(self):
        if self.is_free_shipping is True:
            self.shipping_fee = 0
            return self
        if self.is_free_shipping is False and self.shipping_fee is None:
            raise ValueError("shipping_fee is required when is_free_shipping is false")
        if self.shipping_fee is not None and float(self.shipping_fee) < 0:
            raise ValueError("shipping_fee must be >= 0")
        return self

class StoreMinimal(BaseModel):
    id: int
    name: str
    min_order_total: Optional[float] = None
    order_shipping_fee: Optional[float] = None
    class Config:
        from_attributes = True

class UserMinimal(BaseModel):
    id: int
    full_name: Optional[str] = None
    class Config:
        from_attributes = True

class ProductReviewBase(BaseModel):
    rating: int
    comment: Optional[str] = None

class ProductReviewCreate(ProductReviewBase):
    pass

class ProductReview(ProductReviewBase):
    id: int
    product_id: int
    user_id: int
    user: Optional[UserMinimal] = None
    is_reported: bool = False
    report_reason: Optional[str] = None
    reported_at: Optional[datetime] = None
    created_at: datetime
    class Config:
        from_attributes = True


class StoreReviewStats(BaseModel):
    average_rating: float = 0.0
    total_reviews: int = 0
    rating_distribution: dict[int, int] = {}


class StoreReviewList(BaseModel):
    reviews: List[ProductReview]
    stats: StoreReviewStats


class ReviewReport(BaseModel):
    reason: Optional[str] = None

class Product(ProductBase):
    id: int
    inventory: Optional[Inventory] = None
    category: Optional[Category] = None
    store: Optional[StoreMinimal] = None
    reviews: List[ProductReview] = []
    images: List[ProductImage] = []
    created_at: datetime
    
    class Config:
        from_attributes = True

# Cart Schemas
class CartItemBase(BaseModel):
    product_id: int
    quantity: int = 1

class CartItemCreate(CartItemBase):
    pass

class CartItem(CartItemBase):
    id: int
    cart_id: int
    product: Optional[Product] = None
    
    class Config:
        from_attributes = True

class Cart(BaseModel):
    id: int
    user_id: int
    items: List[CartItem] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
