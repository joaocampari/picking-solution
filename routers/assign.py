"""
Rotas para alocação automática de devices
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
import csv
import io
from models.database import get_db
from schemas.assignment_schemas import AssignmentRequest, AssignmentResponse
from services.assignment_service import AssignmentService

router = APIRouter(prefix="/assign", tags=["assign"])


@router.post("/auto", response_model=AssignmentResponse)
async def assign_devices_auto(
    request: AssignmentRequest = None,
    csv_file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """
    Aloca automaticamente devices em slots livres
    Pode receber lista de device_ids no body ou upload de CSV
    """
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
        return AssignmentResponse(
            assigned=[],
            failed=[],
            current_position=None,
            error="Nenhum device_id fornecido"
        )

    # Chamar serviço de alocação
    result = AssignmentService.assign_devices_auto(db, unique_device_ids)

    # Converter para formato de response
    return AssignmentResponse(
        assigned=[
            {
                "device_id": item["device_id"],
                "slot_id": item["slot_id"],
                "human_code": item["human_code"],
                "row": item["row"],
                "col": item["col"]
            }
            for item in result["assigned"]
        ],
        failed=result.get("failed", []),
        current_position=result.get("current_position"),
        error=result.get("error")
    )

