from typing import Optional, Any
from pydantic import BaseModel
from datetime import datetime

class NotificationBase(BaseModel):
    title: str
    message: str
    data: Optional[Any] = None
    type: Optional[str] = None
    store_id: Optional[int] = None

class NotificationCreate(NotificationBase):
    user_id: int

class Notification(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
