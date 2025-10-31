from pydantic import BaseModel
from typing import List, Optional


class PickingPlanRequest(BaseModel):
    """Request para criação de plano de picking"""
    device_ids: List[str]


class PickingItem(BaseModel):
    """Item do plano de picking"""
    device_id: str
    slot_id: int
    human_code: str
    row: int
    col: int
    distance_from_prev: float
    cumulative_distance: float


class StartPosition(BaseModel):
    """Posição de início"""
    slot_id: int
    human_code: str


class PickingPlanResponse(BaseModel):
    """Response do plano de picking"""
    route: List[PickingItem]
    total_distance: float
    return_distance: Optional[float] = None
    start_position: Optional[StartPosition] = None
    error: Optional[str] = None

