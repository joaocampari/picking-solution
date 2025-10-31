"""
Rotas para scan IN/OUT de devices
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models.database import get_db
from models.slot import Slot
from models.device import Device, DeviceStatus
from models.movement import Movement, MovementType
from schemas.scan_schemas import ScanInRequest, ScanOutRequest, ScanResponse
from services.assignment_service import AssignmentService
from services.picking_service import PickingService

router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("/in", response_model=ScanResponse)
async def scan_in(
    request: ScanInRequest,
    db: Session = Depends(get_db)
):
    """
    Scan IN: faz entrada de device (aloca automaticamente se não informado slot)
    """
    device_id = request.device_id
    slot_human_code = request.slot_human_code

    # Se slot foi informado, usar ele
    if slot_human_code:
        slot = db.query(Slot).filter(Slot.human_code == slot_human_code).first()
        if not slot:
            return ScanResponse(
                success=False,
                device_id=device_id,
                message="",
                error=f"Slot {slot_human_code} não encontrado"
            )
        if slot.occupied:
            return ScanResponse(
                success=False,
                device_id=device_id,
                message="",
                error=f"Slot {slot_human_code} já está ocupado"
            )
    else:
        # Alocar automaticamente no slot livre mais próximo do ponto dinâmico (último movimento)
        start_slot = AssignmentService.get_dynamic_start_slot(db)
        if not start_slot:
            return ScanResponse(
                success=False,
                device_id=device_id,
                message="",
                error="Nenhum slot disponível para alocação"
            )
        slot = AssignmentService.find_nearest_free_slot(db, start_slot)
        if not slot:
            return ScanResponse(
                success=False,
                device_id=device_id,
                message="",
                error="Nenhum slot livre disponível"
            )

    try:
        # Buscar ou criar device
        device = db.query(Device).filter(Device.device_id == device_id).first()

        if not device:
            device = Device(
                device_id=device_id,
                status=DeviceStatus.IN_STOCK,
                slot_id=slot.id
            )
            db.add(device)
        else:
            # Se device já está em um slot, liberar o slot anterior
            if device.slot_id:
                old_slot = db.query(Slot).filter(Slot.id == device.slot_id).first()
                if old_slot:
                    old_slot.occupied = False

            device.status = DeviceStatus.IN_STOCK
            device.slot_id = slot.id

        # Marcar slot como ocupado
        slot.occupied = True

        # Registrar movimento
        movement = Movement(
            device_id=device_id,
            from_slot_id=None,
            to_slot_id=slot.id,
            type=MovementType.CHECK_IN,
            meta_json={"auto_allocated": slot_human_code is None}
        )
        db.add(movement)

        db.commit()

        return ScanResponse(
            success=True,
            device_id=device_id,
            message=f"Device {device_id} alocado em {slot.human_code}",
            slot_id=slot.id,
            slot_human_code=slot.human_code
        )

    except Exception as e:
        db.rollback()
        return ScanResponse(
            success=False,
            device_id=device_id,
            message="",
            error=f"Erro ao fazer scan IN: {str(e)}"
        )


@router.post("/out", response_model=ScanResponse)
async def scan_out(
    request: ScanOutRequest,
    db: Session = Depends(get_db)
):
    """
    Scan OUT: faz saída de device (libera slot)
    """
    device_id = request.device_id

    # Chamar serviço de picking que já faz isso
    result = PickingService.mark_device_picked(db, device_id)

    if result.get("success"):
        return ScanResponse(
            success=True,
            device_id=device_id,
            message=f"Device {device_id} coletado e slot {result.get('slot_freed')} liberado",
            slot_id=result.get("slot_freed"),
            slot_human_code=result.get("human_code")
        )
    else:
        return ScanResponse(
            success=False,
            device_id=device_id,
            message="",
            error=result.get("error", "Erro desconhecido")
        )

