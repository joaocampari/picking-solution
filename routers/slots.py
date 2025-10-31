"""
Rotas para gerenciamento de slots
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List
from models.database import get_db
from models.slot import Slot
from models.aisle import Aisle
from services.distance_service import DistanceService
from services.assignment_service import AssignmentService
from schemas.slot_schemas import SlotResponse
import os

router = APIRouter(prefix="/slots", tags=["slots"])


@router.get("/available", response_model=List[SlotResponse])
async def get_available_slots(
    limit: int = Query(50, ge=1, le=1000),
    start_rua: Optional[int] = Query(None, ge=1, le=3),
    start_prateleira: Optional[str] = Query(None),
    start_linha: Optional[int] = Query(None, ge=1, le=24),
    start_coluna: Optional[int] = Query(None, ge=1, le=40),
    db: Session = Depends(get_db)
):
    """
    Lista slots livres ordenados pelo percurso mais curto
    a partir de um ponto inicial (padrão RUA1/P1/L1/C1)
    """
    # Determinar ponto inicial
    if start_rua and start_prateleira and start_linha and start_coluna:
        from services.codecs import row_to_letter
        row_letter = row_to_letter(start_linha)
        human_code = f"R{start_rua}-{start_prateleira}-{row_letter}-C{start_coluna}"
        start_slot = db.query(Slot).filter(Slot.human_code == human_code).first()
    else:
        start_slot = AssignmentService.get_default_start_slot(db)

    if not start_slot:
        # Se não encontrar ponto inicial, retornar slots livres sem ordenação
        slots = db.query(Slot).filter(Slot.occupied == False).limit(limit).all()
        return [SlotResponse(
            id=s.id,
            aisle_id=s.aisle_id,
            shelf_id=s.shelf_id,
            row_index=s.row_index,
            col_index=s.col_index,
            human_code=s.human_code,
            occupied=s.occupied
        ) for s in slots]

    # Buscar slots livres e calcular distâncias
    free_slots = db.query(Slot).filter(Slot.occupied == False).all()

    slots_with_distance = [
        (slot, DistanceService.calculate_distance(start_slot, slot))
        for slot in free_slots
    ]

    # Ordenar por distância
    slots_with_distance.sort(key=lambda x: x[1])

    # Limitar resultados
    slots_with_distance = slots_with_distance[:limit]

    return [SlotResponse(
        id=s.id,
        aisle_id=s.aisle_id,
        shelf_id=s.shelf_id,
        row_index=s.row_index,
        col_index=s.col_index,
        human_code=s.human_code,
        occupied=s.occupied
    ) for s, _ in slots_with_distance]

