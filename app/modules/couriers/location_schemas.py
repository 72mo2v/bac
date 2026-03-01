from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CourierLocationIn(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: Optional[float] = None
    heading: Optional[float] = None
    speed: Optional[float] = None
    order_id: Optional[int] = None


class CourierLocationOut(BaseModel):
    id: int
    courier_user_id: int
    order_id: Optional[int] = None
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    heading: Optional[float] = None
    speed: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True

