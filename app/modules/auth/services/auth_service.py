from datetime import timedelta, datetime, timezone
import uuid
from app.core import security
from app.core.exceptions import UnauthorizedException, BusinessRuleException
from app.modules.auth.repositories.user_repository import UserRepository
from app.modules.auth.schemas import UserCreate, Token
from app.infrastructure.email import email_service
from app.modules.auth.models import UserAccessStatus, UserRole

class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register_user(self, user_in: UserCreate):
        existing_user = await self.user_repo.get_by_email(user_in.email)
        if existing_user:
            raise BusinessRuleException("User with this email already exists")
        
        user_data = user_in.model_dump()
        user_data.pop("admin_role_id", None)
        password = user_data.pop("password")
        user_data["hashed_password"] = security.get_password_hash(password)
        user_data["is_verified"] = False # Initial state
        
        user = await self.user_repo.create(user_data)
        
        # Trigger Verification Email
        verification_token = str(uuid.uuid4()) # In real app, store this in DB/Redis
        await email_service.send_verification_email(user.email, verification_token)
        
        return await self.user_repo.get_profile(user.id)

    async def authenticate(self, email: str, password: str, app: str | None = None) -> Token:
        generic_msg = "البريد او كلمة المرور غير صحيحة او هذا الحساب غير موجود"

        user = await self.user_repo.get_by_email(email)
        if not user or not security.verify_password(password, user.hashed_password):
            raise UnauthorizedException(generic_msg)

        if not user.is_active:
            raise UnauthorizedException(generic_msg)

        if user.access_status == UserAccessStatus.BLOCKED:
            raise UnauthorizedException(generic_msg)

        if user.access_status == UserAccessStatus.SUSPENDED:
            until = user.suspended_until
            now = datetime.now(timezone.utc)
            if until is None or until > now:
                raise UnauthorizedException(generic_msg)

        if app:
            app = app.lower().strip()
            if app == "admin":
                if user.role != UserRole.SUPER_ADMIN:
                    raise UnauthorizedException(generic_msg)
            elif app == "merchant":
                if user.role not in [UserRole.STORE_OWNER, UserRole.STORE_ADMIN, UserRole.SUPER_ADMIN]:
                    raise UnauthorizedException(generic_msg)
            elif app == "client":
                if user.role != UserRole.CUSTOMER:
                    raise UnauthorizedException(generic_msg)
            else:
                raise UnauthorizedException(generic_msg)

        access_token = security.create_access_token(
            subject=user.id, 
            role=user.role.value
        )
        refresh_token = security.create_refresh_token(subject=user.id)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
