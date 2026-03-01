from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from pathlib import Path
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.payments.schemas import Payment, PaymentCreate, PaymentUpdate
from app.modules.payments.repositories.payment_repository import PaymentRepository
from app.modules.orders.repositories.order_repository import OrderRepository
from app.modules.payments.services.payment_service import PaymentService

router = APIRouter()

async def get_payment_service(db: AsyncSession = Depends(get_db)) -> PaymentService:
    p_repo = PaymentRepository(db)
    o_repo = OrderRepository(db)
    return PaymentService(p_repo, o_repo)

@router.post("/", response_model=Payment)
async def create_payment(
    payment_in: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    service: PaymentService = Depends(get_payment_service)
):
    created = await service.create_payment(payment_in)
    await db.commit()
    loaded = await service.payment_repo.get_with_method(created.id)
    return loaded or created

@router.get("/{payment_id}", response_model=Payment)
async def get_payment(
    payment_id: int,
    service: PaymentService = Depends(get_payment_service)
):
    payment = await service.payment_repo.get_with_method(payment_id)
    return payment

@router.patch("/{payment_id}/process", response_model=Payment)
async def process_payment(
    payment_id: int,
    update: PaymentUpdate,
    db: AsyncSession = Depends(get_db),
    service: PaymentService = Depends(get_payment_service)
):
    updated = await service.process_payment(payment_id, update)
    await db.commit()
    loaded = await service.payment_repo.get_with_method(updated.id)
    return loaded or updated


@router.post("/{payment_id}/proof/upload", response_model=Payment)
async def upload_payment_proof(
    payment_id: int,
    request: Request,
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    service: PaymentService = Depends(get_payment_service),
):
    payment = await service.payment_repo.get(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    suffix = Path(image.filename or "").suffix.lower()
    if suffix not in [".png", ".jpg", ".jpeg", ".webp"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    content = await image.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")

    uploads_dir = Path(__file__).resolve().parents[4] / "uploads" / "payments" / str(payment_id)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}{suffix}"
    dest = uploads_dir / safe_name
    dest.write_bytes(content)

    payment.proof_image_url = f"/uploads/payments/{payment_id}/{safe_name}"
    updated = await service.payment_repo.update(payment, {"proof_image_url": payment.proof_image_url})
    await db.commit()
    loaded = await service.payment_repo.get_with_method(updated.id)
    return loaded or updated
