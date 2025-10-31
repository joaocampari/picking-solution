from pydantic import BaseModel
from typing import List, Optional, Dict


class AssignmentRequest(BaseModel):
    """Request para alocação automática de devices"""
    device_ids: List[str]


class AssignedItem(BaseModel):
    """Item alocado"""
    device_id: str
    slot_id: int
    human_code: str
    row: int
    col: int


class CurrentPosition(BaseModel):
    """Posição atual após alocação"""
    slot_id: int
    human_code: str


class AssignmentResponse(BaseModel):
    """Response da alocação automática"""
    assigned: List[AssignedItem]
    failed: List[str]
    current_position: Optional[CurrentPosition] = None
    error: Optional[str] = None

