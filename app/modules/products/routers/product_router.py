from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, Request, Form
from pathlib import Path
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.middleware import get_store_id
from app.modules.products.schemas import (
    Product, ProductCreate, ProductUpdate, 
    Category, CategoryCreate, 
    Inventory, InventoryUpdate,
    ProductReview, ProductReviewCreate, LowStockProduct,
    CategoryReorderRequest
)
from app.modules.products.repositories.product_repository import (
    ProductRepository, InventoryRepository, CategoryRepository, ProductReviewRepository, ProductImageRepository
)
from app.modules.products.services.product_service import ProductService
from app.core.deps import get_current_active_user, require_current_store_id
from app.core.middleware import set_store_id
from app.modules.auth.models import User, UserRole, StoreUser
from app.modules.products.models import Product as ProductModel, Inventory as InventoryModel, Category as CategoryModel

router = APIRouter()

# --- Re-use Existing Dependencies or add new ones ---
async def get_product_service(db: AsyncSession = Depends(get_db)) -> ProductService:
    prod_repo = ProductRepository(db)
    inv_repo = InventoryRepository(db)
    return ProductService(prod_repo, inv_repo)

async def get_review_repo(db: AsyncSession = Depends(get_db)) -> ProductReviewRepository:
    return ProductReviewRepository(db)

async def get_product_image_repo(db: AsyncSession = Depends(get_db)) -> ProductImageRepository:
    return ProductImageRepository(db)

# --- Category Routes (Existing) ---
@router.post("/categories", response_model=Category)
async def create_category(
    category_in: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    store_id: int = Depends(require_current_store_id),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough privileges")

    repo = CategoryRepository(db)
    return await repo.create(category_in.model_dump())

@router.get("/categories", response_model=List[Category])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN, UserRole.CUSTOMER]:
        raise HTTPException(status_code=403, detail="Not enough privileges")

    if current_user.role in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        store_id = await require_current_store_id(current_user=current_user, db=db)
    else:
        store_id = None
        set_store_id(None)

    q = select(CategoryModel).order_by(CategoryModel.display_order.asc(), CategoryModel.id.asc())
    if store_id:
        q = q.where(CategoryModel.store_id == store_id)
    result = await db.execute(q)
    return list(result.scalars().all())


@router.post("/categories/reorder")
async def reorder_categories(
    payload: CategoryReorderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough privileges")

    result = await db.execute(select(StoreUser.store_id).where(StoreUser.user_id == current_user.id))
    store_id = result.scalar_one_or_none()
    if not store_id:
        raise HTTPException(status_code=404, detail="No store associated with this user")

    # Apply updates only to categories that belong to this store
    ids = [item.id for item in payload.items]
    if not ids:
        return {"status": "success"}

    cat_rows = await db.execute(
        select(CategoryModel).where(
            CategoryModel.id.in_(ids),
            CategoryModel.store_id == store_id,
        )
    )
    cats = list(cat_rows.scalars().all())
    cat_by_id = {c.id: c for c in cats}

    for item in payload.items:
        cat = cat_by_id.get(item.id)
        if cat:
            cat.display_order = item.display_order
            db.add(cat)

    await db.commit()
    return {"status": "success"}

# --- Product Routes ---
@router.get("/me/low-stock", response_model=List[LowStockProduct])
async def list_my_low_stock_products(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough privileges")

    result = await db.execute(select(StoreUser.store_id).where(StoreUser.user_id == current_user.id))
    store_id = result.scalar_one_or_none()
    if not store_id:
        raise HTTPException(status_code=404, detail="No store associated with this user")

    q = (
        select(
            ProductModel.id,
            ProductModel.name,
            ProductModel.image_url,
            InventoryModel.quantity,
            InventoryModel.low_stock_threshold,
        )
        .join(InventoryModel, InventoryModel.product_id == ProductModel.id)
        .where(
            ProductModel.store_id == store_id,
            InventoryModel.store_id == store_id,
            InventoryModel.quantity <= InventoryModel.low_stock_threshold,
        )
        .order_by(InventoryModel.quantity.asc())
    )
    rows = (await db.execute(q)).all()
    return [
        LowStockProduct(
            product_id=row.id,
            name=row.name,
            quantity=row.quantity,
            low_stock_threshold=row.low_stock_threshold,
            image_url=row.image_url,
        )
        for row in rows
    ]

@router.post("", response_model=Product)
@router.post("/", response_model=Product)
async def create_product(
    product_in: ProductCreate,
    service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_active_user),
    store_id: int = Depends(require_current_store_id),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough privileges")

    return await service.create_product(product_in)

@router.get("", response_model=List[Product])
@router.get("/", response_model=List[Product])
async def list_products(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN, UserRole.CUSTOMER]:
        raise HTTPException(status_code=403, detail="Not enough privileges")

    if current_user.role in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        await require_current_store_id(current_user=current_user, db=service.product_repo.db)
    else:
        set_store_id(None)

    return await service.product_repo.get_multi_with_inventory(
        skip=skip, limit=limit, search=search, category_id=category_id
    )

@router.get("/{product_id}", response_model=Product)
async def get_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN, UserRole.CUSTOMER]:
        raise HTTPException(status_code=403, detail="Not enough privileges")

    if current_user.role in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        await require_current_store_id(current_user=current_user, db=service.product_repo.db)
    else:
        set_store_id(None)

    return await service.product_repo.get_with_inventory(product_id)


@router.patch("/{product_id}", response_model=Product)
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    store_id: int = Depends(require_current_store_id),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough privileges")

    prod_repo = ProductRepository(db)
    product = await prod_repo.get_with_inventory(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if current_user.role != UserRole.SUPER_ADMIN and getattr(product, "store_id", None) != store_id:
        raise HTTPException(status_code=403, detail="Product does not belong to your store")

    patch = payload.model_dump(exclude_unset=True)
    if "slug" in patch and (patch["slug"] is None or str(patch["slug"]).strip() in ["", "-"]):
        patch.pop("slug", None)

    updated = await prod_repo.update(product, patch)
    return await prod_repo.get_with_inventory(updated.id)


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    store_id: int = Depends(require_current_store_id),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough privileges")

    prod_repo = ProductRepository(db)
    product = await prod_repo.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if current_user.role != UserRole.SUPER_ADMIN and getattr(product, "store_id", None) != store_id:
        raise HTTPException(status_code=403, detail="Product does not belong to your store")

    deleted = await prod_repo.remove(product_id)
    await db.commit()
    return {"status": "success", "deleted": bool(deleted)}

@router.patch("/{product_id}/inventory", response_model=Inventory)
async def update_inventory(
    product_id: int,
    inventory_in: InventoryUpdate,
    db: AsyncSession = Depends(get_db),
    service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_active_user),
    store_id: int = Depends(require_current_store_id),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough privileges")

    product = await service.product_repo.get_with_inventory(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if current_user.role != UserRole.SUPER_ADMIN and getattr(product, "store_id", None) != store_id:
        raise HTTPException(status_code=403, detail="Product does not belong to your store")

    return await service.update_inventory(product_id, inventory_in)


@router.post("/{product_id}/images/upload", response_model=Product)
async def upload_product_image(
    product_id: int,
    request: Request,
    image: UploadFile = File(...),
    display_order: int = Form(0),
    is_primary: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    store_id: int = Depends(require_current_store_id),
    image_repo: ProductImageRepository = Depends(get_product_image_repo),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough privileges")

    product_result = await db.execute(select(ProductModel).where(ProductModel.id == product_id))
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if current_user.role != UserRole.SUPER_ADMIN and getattr(product, "store_id", None) != store_id:
        raise HTTPException(status_code=403, detail="Product does not belong to your store")

    suffix = Path(image.filename or "").suffix.lower()
    if suffix not in [".png", ".jpg", ".jpeg", ".webp"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    content = await image.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")

    uploads_dir = Path(__file__).resolve().parents[4] / "uploads" / "products" / str(product_id)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}{suffix}"
    dest = uploads_dir / safe_name
    dest.write_bytes(content)

    base = str(request.base_url).rstrip("/")
    image_url = f"{base}/uploads/products/{product_id}/{safe_name}"

    await image_repo.create(
        {
            "product_id": product_id,
            "image_url": image_url,
            "display_order": display_order,
            "is_primary": is_primary,
        }
    )

    if is_primary:
        product.image_url = image_url
        db.add(product)

    await db.commit()

    prod_repo = ProductRepository(db)
    return await prod_repo.get_with_inventory(product_id)

# --- Review Routes ---
@router.post("/{product_id}/reviews", response_model=ProductReview)
async def create_product_review(
    product_id: int,
    review_in: ProductReviewCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = ProductReviewRepository(db)
    review_data = review_in.model_dump()
    review_data["product_id"] = product_id
    review_data["user_id"] = current_user.id
    return await repo.create(review_data)
