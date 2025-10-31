"""
Rotas para consulta de devices
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from models.database import get_db
from models.device import Device
from models.slot import Slot
from schemas.device_schemas import DeviceResponse

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    db: Session = Depends(get_db)
):
    """
    Busca device por device_id
    """
    device = db.query(Device).filter(Device.device_id == device_id).first()

    if not device:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Device {device_id} não encontrado")

    slot_human_code = None
    row = None
    col = None

    if device.slot_id:
        slot = db.query(Slot).filter(Slot.id == device.slot_id).first()
        if slot:
            slot_human_code = slot.human_code
            row = slot.row_index
            col = slot.col_index

    return DeviceResponse(
        id=device.id,
        device_id=device.device_id,
        status=device.status,
        slot_id=device.slot_id,
        slot_human_code=slot_human_code,
        row=row,
        col=col
    )


@router.get("/search/query")
async def search_devices(
    query: str = Query(..., description="Busca por device_id ou human_code do slot"),
    db: Session = Depends(get_db)
):
    """
    Busca devices por device_id ou human_code do slot
    """
    # Buscar por device_id
    devices_by_id = db.query(Device).filter(
        Device.device_id.ilike(f"%{query}%")
    ).all()

    # Buscar por human_code do slot
    slots = db.query(Slot).filter(
        Slot.human_code.ilike(f"%{query}%")
    ).all()
    slot_ids = [s.id for s in slots]
    devices_by_slot = db.query(Device).filter(
        Device.slot_id.in_(slot_ids)
    ).all() if slot_ids else []

    # Combinar resultados (sem duplicatas)
    all_devices = {}
    for device in devices_by_id:
        all_devices[device.id] = device
    for device in devices_by_slot:
        all_devices[device.id] = device

    results = []
    for device in all_devices.values():
        slot_human_code = None
        row = None
        col = None

        if device.slot_id:
            slot = db.query(Slot).filter(Slot.id == device.slot_id).first()
            if slot:
                slot_human_code = slot.human_code
                row = slot.row_index
                col = slot.col_index

        results.append(DeviceResponse(
            id=device.id,
            device_id=device.device_id,
            status=device.status,
            slot_id=device.slot_id,
            slot_human_code=slot_human_code,
            row=row,
            col=col
        ))

    return {"results": results}

