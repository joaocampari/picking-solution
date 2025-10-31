from pydantic import BaseModel
from typing import Optional
from models.device import DeviceStatus


class DeviceResponse(BaseModel):
    """Response de um device"""
    id: int
    device_id: str
    status: DeviceStatus
    slot_id: Optional[int] = None
    slot_human_code: Optional[str] = None
    row: Optional[int] = None
    col: Optional[int] = None

    class Config:
        from_attributes = True

