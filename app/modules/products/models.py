from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    slug = Column(String, index=True)
    description = Column(Text, nullable=True)
    store_id = Column(Integer, index=True, nullable=True) # Optional: shared categories? or per store? let's keep it per store for flexibility

    parent_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    display_order = Column(Integer, default=0)
    icon_url = Column(String, nullable=True)
    is_visible = Column(Boolean, default=True)

    products = relationship("Product", back_populates="category")
    parent = relationship("Category", remote_side=[id], back_populates="children")
    children = relationship("Category", back_populates="parent")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, index=True, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    name = Column(String, index=True, nullable=False)
    slug = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    compare_at_price = Column(Float, nullable=True)
    sku = Column(String, index=True, nullable=True)
    
    image_url = Column(String, nullable=True)
    is_deal = Column(Boolean, default=False)
    is_bestseller = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    deal_price = Column(Float, nullable=True)
    deal_end_date = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    origin = Column(String, nullable=False, default="LOCAL", index=True)

    is_free_shipping = Column(Boolean, default=True, nullable=False)
    shipping_fee = Column(Float, default=0, nullable=False)

    max_qty_per_order = Column(Integer, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    category = relationship("Category", back_populates="products")
    inventory = relationship("Inventory", back_populates="product", uselist=False, cascade="all, delete-orphan")
    store = relationship("app.modules.stores.models.Store", foreign_keys=[store_id], primaryjoin="Product.store_id == Store.id", viewonly=True)
    reviews = relationship("ProductReview", back_populates="product", cascade="all, delete-orphan")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False)
    image_url = Column(String, nullable=False)
    display_order = Column(Integer, default=0)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="images")

class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), unique=True)
    store_id = Column(Integer, index=True, nullable=False)
    
    quantity = Column(Integer, default=0)
    low_stock_threshold = Column(Integer, default=5)
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    product = relationship("Product", back_populates="inventory")

class ProductReview(Base):
    __tablename__ = "product_reviews"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    rating = Column(Integer, nullable=False) # 1-5
    comment = Column(Text, nullable=True)
    is_reported = Column(Boolean, default=False)
    report_reason = Column(Text, nullable=True)
    reported_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="reviews")
    user = relationship("app.modules.auth.models.User")

class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)

    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")
