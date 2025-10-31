from pydantic import BaseModel
from typing import List, Optional


class SlotResponse(BaseModel):
    """Response de um slot"""
    id: int
    aisle_id: int
    shelf_id: int
    row_index: int
    col_index: int
    human_code: str
    occupied: bool


class AvailableSlotsRequest(BaseModel):
    """Request para buscar slots livres próximos"""
    limit: int = 50
    start_rua: Optional[int] = None
    start_prateleira: Optional[str] = None
    start_linha: Optional[int] = None
    start_coluna: Optional[int] = None

