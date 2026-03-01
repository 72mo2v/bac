from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.base_repository import BaseRepository
from app.modules.auth.models import User, Address, UserSession
from app.core.security import get_password_hash

class UserRepository(BaseRepository[User]):
    def __init__(self, db):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        query = select(User).filter(User.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_profile(self, user_id: int) -> Optional[User]:
        query = select(User).options(
            selectinload(User.addresses),
            selectinload(User.admin_details)
        ).filter(User.id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update(self, db_obj: User, obj_in: dict) -> User:
        if "password" in obj_in and obj_in["password"]:
            password = obj_in.pop("password")
            obj_in["hashed_password"] = get_password_hash(password)
        elif "password" in obj_in:
            obj_in.pop("password")
            
        return await super().update(db_obj, obj_in)

class AddressRepository(BaseRepository[Address]):
    def __init__(self, db):
        super().__init__(Address, db)

    async def get_user_addresses(self, user_id: int) -> List[Address]:
        query = select(Address).filter(Address.user_id == user_id).order_by(Address.is_default.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())


class UserSessionRepository(BaseRepository[UserSession]):
    def __init__(self, db):
        super().__init__(UserSession, db)

    async def list_for_user(self, user_id: int) -> List[UserSession]:
        query = select(UserSession).filter(UserSession.user_id == user_id).order_by(UserSession.last_active.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def clear_current(self, user_id: int) -> None:
        from sqlalchemy import update
        await self.db.execute(
            update(UserSession)
            .where(UserSession.user_id == user_id)
            .values(is_current=False)
        )
