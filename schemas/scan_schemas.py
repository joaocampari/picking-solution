from pydantic import BaseModel
from typing import Optional


class ScanInRequest(BaseModel):
    """Request para scan IN (entrada de device)"""
    device_id: str
    slot_human_code: Optional[str] = None  # Se não fornecido, aloca automaticamente


class ScanOutRequest(BaseModel):
    """Request para scan OUT (saída de device)"""
    device_id: str


class ScanResponse(BaseModel):
    """Response do scan"""
    success: bool
    device_id: str
    message: str
    slot_id: Optional[int] = None
    slot_human_code: Optional[str] = None
    error: Optional[str] = None

