from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, File, Form
from app.core.deps import get_current_active_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.modules.auth.schemas import UserCreate, Token, User as UserSchema, UserLogin, UserUpdate, UserSession as UserSessionSchema, PasswordResetRequest
from app.modules.auth.models import User as UserModel, UserSession, UserRole, Address as AddressModel
from app.modules.auth.repositories.user_repository import UserRepository, UserSessionRepository
from app.modules.auth.services.auth_service import AuthService
from app.infrastructure.email import email_service
import uuid
from pathlib import Path
from app.modules.notifications.repositories.notification_repository import NotificationRepository
from app.modules.notifications.services.notification_service import NotificationService

router = APIRouter()

async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    user_repo = UserRepository(db)
    return AuthService(user_repo)

@router.post("/register", response_model=UserSchema)
async def register(
    user_in: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Register a new user."""
    user = await auth_service.register_user(user_in)
    await db.commit()
    return user


@router.post("/register-with-docs", response_model=UserSchema)
async def register_with_docs(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone_number: str = Form(...),
    home_address: str = Form(...),
    home_city: str = Form(...),
    shop_address: str = Form(...),
    shop_city: str = Form(...),
    id_card: UploadFile = File(...),
    store_front: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> Any:
    user = await auth_service.register_user(UserCreate(full_name=full_name, email=email, password=password))

    uploads_dir = Path(__file__).resolve().parents[4] / "uploads" / "user_verification" / str(user.id)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    def _build_public_url(relative_path: str) -> str:
        base = str(request.base_url).rstrip("/")
        return f"{base}/uploads/{relative_path.lstrip('/')}"

    async def _save(file: UploadFile) -> str:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in [".png", ".jpg", ".jpeg", ".webp"]:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        safe_name = f"{uuid.uuid4().hex}{suffix}"
        dest = uploads_dir / safe_name
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large")
        dest.write_bytes(content)
        rel = f"user_verification/{user.id}/{safe_name}"
        return _build_public_url(rel)

    id_card_url = await _save(id_card)
    store_front_photo_url = await _save(store_front)

    user_repo = UserRepository(db)
    await user_repo.update(
        user,
        {
            "phone_number": phone_number,
            "id_card_url": id_card_url,
            "store_front_photo_url": store_front_photo_url,
        },
    )

    db.add(
        AddressModel(
            user_id=user.id,
            title="Home",
            full_address=home_address,
            city=home_city,
            country="Egypt",
            phone=phone_number,
            is_default=True,
        )
    )
    db.add(
        AddressModel(
            user_id=user.id,
            title="Shop",
            full_address=shop_address,
            city=shop_city,
            country="Egypt",
            phone=phone_number,
            is_default=False,
        )
    )
    await db.commit()

    notif_service = NotificationService(NotificationRepository(db))
    admin_users = await db.execute(select(UserModel).where(UserModel.role == UserRole.SUPER_ADMIN))
    for admin in admin_users.scalars().all():
        await notif_service.notify_user(
            user_id=admin.id,
            title="طلب توثيق عميل",
            message=f"قام المستخدم {user.full_name or user.email} برفع مستندات التوثيق.",
            type="user_verification",
            data={"user_id": user.id},
        )

    return await user_repo.get_profile(user.id)


@router.post("/forgot-password")
async def forgot_password(
    payload: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(payload.email)
    if user:
        token = str(uuid.uuid4())
        await email_service.send_password_reset_email(user.email, token)
    return {"status": "success"}

@router.post("/login", response_model=Token)
async def login(
    login_data: UserLogin,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Login and get access token."""
    token = await auth_service.authenticate(login_data.email, login_data.password, login_data.app)

    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(login_data.email)
    if user:
        session_repo = UserSessionRepository(db)
        await session_repo.clear_current(user.id)
        user_agent = request.headers.get("user-agent", "")
        device_type = "mobile" if "Mobile" in user_agent else "desktop"
        session = UserSession(
            user_id=user.id,
            device_type=device_type,
            device_name=user_agent[:120] if user_agent else "Unknown",
            ip_address=request.client.host if request.client else None,
            is_current=True
        )
        db.add(session)
        await db.commit()

    return token

@router.get("/me", response_model=UserSchema)
async def get_me(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get current user with profile details."""
    user_repo = UserRepository(db)
    return await user_repo.get_profile(current_user.id)

@router.patch("/me", response_model=UserSchema)
async def update_profile(
    user_in: UserUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update current user profile."""
    user_repo = UserRepository(db)
    update_data = user_in.model_dump(exclude_unset=True)
    await user_repo.update(current_user, update_data)
    return await user_repo.get_profile(current_user.id)

# Address Endpoints
from app.modules.auth.schemas import Address as AddressSchema, AddressCreate, AddressUpdate
from app.modules.auth.models import Address as AddressModel
from app.modules.auth.repositories.user_repository import AddressRepository

@router.get("/me/addresses", response_model=List[AddressSchema])
async def get_my_addresses(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get current user addresses."""
    address_repo = AddressRepository(db)
    return await address_repo.get_user_addresses(current_user.id)

@router.post("/me/addresses", response_model=AddressSchema)
async def add_address(
    address_in: AddressCreate,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Add a new address."""
    address_repo = AddressRepository(db)
    address_data = address_in.model_dump()
    address_data["user_id"] = current_user.id
    
    # If this is the default address, unset others
    if address_data.get("is_default"):
        from sqlalchemy import update
        await db.execute(
            update(AddressModel)
            .where(AddressModel.user_id == current_user.id)
            .values(is_default=False)
        )
        
    return await address_repo.create(address_data)

@router.patch("/me/addresses/{address_id}", response_model=AddressSchema)
async def update_address(
    address_id: int,
    address_in: AddressUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update an address."""
    address_repo = AddressRepository(db)
    address = await address_repo.get(address_id)
    if not address or address.user_id != current_user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Address not found")
        
    address_data = address_in.model_dump(exclude_unset=True)
    
    # If setting as default, unset others
    if address_data.get("is_default"):
        from sqlalchemy import update
        await db.execute(
            update(AddressModel)
            .where(AddressModel.user_id == current_user.id)
            .values(is_default=False)
        )
        
    return await address_repo.update(address, address_data)

@router.delete("/me/addresses/{address_id}")
async def delete_address(
    address_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Delete an address."""
    address_repo = AddressRepository(db)
    address = await address_repo.get(address_id)
    if not address or address.user_id != current_user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Address not found")
    
    await address_repo.remove(address_id)
    return {"status": "success"}

from app.modules.auth.schemas import PasswordChange
from app.core.security import verify_password, get_password_hash

@router.post("/me/change-password")
async def change_password(
    password_in: PasswordChange,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Change user password."""
    if not verify_password(password_in.current_password, current_user.hashed_password):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="كلمة المرور الحالية غير صحيحة")
    
    user_repo = UserRepository(db)
    await user_repo.update(current_user, {"password": password_in.new_password})
    return {"status": "success"}


@router.get("/sessions", response_model=List[UserSessionSchema])
async def list_sessions(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    session_repo = UserSessionRepository(db)
    return await session_repo.list_for_user(current_user.id)


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    session_repo = UserSessionRepository(db)
    session = await session_repo.get(session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    await session_repo.remove(session_id)
    return {"status": "success"}


@router.delete("/sessions")
async def revoke_other_sessions(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    from sqlalchemy import delete
    await db.execute(
        delete(UserSession)
        .where(UserSession.user_id == current_user.id)
        .where(UserSession.is_current == False)
    )
    await db.commit()
    return {"status": "success"}
