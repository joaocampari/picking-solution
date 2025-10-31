"""
Rotas para picking (coleta de devices)
"""
from fastapi import APIRouter, Depends, UploadFile, File, Response
from sqlalchemy.orm import Session
from typing import List
import csv
import io
import json
from models.database import get_db
from schemas.picking_schemas import PickingPlanRequest, PickingPlanResponse
from services.picking_service import PickingService

router = APIRouter(prefix="/picking", tags=["picking"])

# Guardar último plano em memória (em produção usar cache/DB)
_last_picking_plan = None


@router.post("/plan", response_model=PickingPlanResponse)
async def create_picking_plan(
    request: PickingPlanRequest = None,
    csv_file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """
    Cria plano de picking para uma lista de devices
    Pode receber lista de device_ids no body ou upload de CSV
    """
    global _last_picking_plan

    device_ids = []

    # Se há arquivo CSV, processar primeiro
    if csv_file:
        contents = await csv_file.read()
        text = contents.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(text))
        for row in csv_reader:
            if row:  # Ignorar linhas vazias
                device_ids.extend([d.strip() for d in row if d.strip()])

    # Se há request com device_ids, usar também
    if request and request.device_ids:
        device_ids.extend(request.device_ids)

    # Remover duplicatas mantendo ordem
    seen = set()
    unique_device_ids = []
    for did in device_ids:
        if did and did not in seen:
            seen.add(did)
            unique_device_ids.append(did)

    if not unique_device_ids:
        return PickingPlanResponse(
            route=[],
            total_distance=0.0,
            return_distance=None,
            start_position=None,
            error="Nenhum device_id fornecido"
        )

    # Criar plano de picking
    result = PickingService.create_picking_plan(db, unique_device_ids)

    # Marcar todos como IN_TRANSIT
    PickingService.mark_devices_in_transit(db, unique_device_ids)

    # Guardar em memória para exportação e reset
    _last_picking_plan = {
        **result,
        "device_ids": unique_device_ids
    }

    return PickingPlanResponse(
        route=result.get("route", []),
        total_distance=result.get("total_distance", 0.0),
        return_distance=result.get("return_distance"),
        start_position=result.get("start_position"),
        error=result.get("error")
    )


@router.get("/plan.csv")
async def export_picking_plan_csv():
    """
    Exporta o último plano de picking como CSV
    """
    global _last_picking_plan

    if not _last_picking_plan:
        return Response(
            content="Nenhum plano de picking disponível",
            media_type="text/plain",
            status_code=404
        )

    route = _last_picking_plan.get("route", [])

    # Criar CSV em memória
    output = io.StringIO()
    writer = csv.writer(output)

    # Cabeçalho
    writer.writerow([
        "Ordem",
        "Device ID",
        "Slot (Código Humano)",
        "Linha",
        "Coluna",
        "Distância do Anterior",
        "Distância Acumulada"
    ])

    # Dados
    for idx, item in enumerate(route, start=1):
        writer.writerow([
            idx,
            item["device_id"],
            item["human_code"],
            item["row"],
            item["col"],
            f"{item['distance_from_prev']:.2f}",
            f"{item['cumulative_distance']:.2f}"
        ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=picking_plan.csv"}
    )


@router.post("/mark-picked")
async def mark_device_picked(
    device_id: str,
    db: Session = Depends(get_db)
):
    """
    Marca um device como coletado (picked)
    """
    result = PickingService.mark_device_picked(db, device_id)
    return result


@router.post("/mark-in-transit")
async def mark_device_in_transit(
    device_id: str,
    db: Session = Depends(get_db)
):
    result = PickingService.mark_device_in_transit(db, device_id)
    return result


@router.post("/reset")
async def reset_picking_plan(db: Session = Depends(get_db)):
    """Cancela o plano atual: retorna devices IN_TRANSIT para IN_STOCK."""
    global _last_picking_plan
    if not _last_picking_plan or not _last_picking_plan.get("device_ids"):
        return {"success": False, "error": "Nenhum plano ativo"}
    dids = _last_picking_plan.get("device_ids", [])
    result = PickingService.reset_devices_from_transit(db, dids)
    # Limpar plano em memória
    _last_picking_plan = None
    return result

