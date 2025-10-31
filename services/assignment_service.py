"""
Serviço para alocação automática de devices em slots livres
usando algoritmo guloso (sempre ao slot livre mais próximo)
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.slot import Slot
from models.device import Device, DeviceStatus
from models.movement import Movement, MovementType
from services.distance_service import DistanceService
from typing import List, Optional
import os
from dotenv import load_dotenv

load_dotenv()


class AssignmentService:
    """Gerencia alocação automática de devices em slots"""

    @staticmethod
    def get_default_start_slot(db: Session):
        """
        Retorna o slot de início padrão baseado em variáveis de ambiente
        ou padrão RUA1/P1/L1/C1
        """
        start_rua = os.getenv("START_RUA", "1")
        start_prateleira = os.getenv("START_PRATELEIRA", "P1")
        start_linha = int(os.getenv("START_LINHA", "1"))
        start_coluna = int(os.getenv("START_COLUNA", "1"))

        from services.codecs import row_to_letter
        row_letter = row_to_letter(start_linha)

        # Buscar slot pelo human_code
        human_code = f"R{start_rua}-{start_prateleira}-{row_letter}-C{start_coluna}"
        slot = db.query(Slot).filter(Slot.human_code == human_code).first()

        if not slot:
            # Fallback: primeiro slot livre
            slot = db.query(Slot).filter(Slot.occupied == False).order_by(
                Slot.id
            ).first()

        return slot

    @staticmethod
    def get_dynamic_start_slot(db: Session) -> Optional[Slot]:
        """
        Usa o último movimento como ponto atual, priorizando:
        - to_slot_id de CHECK_IN/MOVE (posição atual)
        - from_slot_id de CHECK_OUT (onde estávamos por último)
        Fallback: get_default_start_slot
        """
        last_move = db.query(Movement).order_by(Movement.ts.desc()).first()
        if last_move:
            if last_move.to_slot_id:
                slot = db.query(Slot).filter(Slot.id == last_move.to_slot_id).first()
                if slot:
                    return slot
            if last_move.from_slot_id:
                slot = db.query(Slot).filter(Slot.id == last_move.from_slot_id).first()
                if slot:
                    return slot
        return AssignmentService.get_default_start_slot(db)

    @staticmethod
    def find_nearest_free_slot(db: Session, current_slot: Slot) -> Optional[Slot]:
        """
        Encontra o slot livre mais próximo do slot atual
        Verifica tanto o flag occupied quanto se já existe device usando o slot
        """
        # Buscar IDs de slots já ocupados por devices (flush para garantir que veja objetos pendentes)
        db.flush()
        occupied_slot_ids = [row[0] for row in db.query(Device.slot_id).filter(
            Device.slot_id.isnot(None)
        ).all()]

        # Buscar slots que não estão ocupados E não têm device alocado
        free_slots = db.query(Slot).filter(
            Slot.occupied == False
        ).all()
        
        # Filtrar slots que não estão na lista de ocupados
        if occupied_slot_ids:
            free_slots = [s for s in free_slots if s.id not in occupied_slot_ids]

        if not free_slots:
            return None

        # Calcular distância e aplicar desempate priorizando mesma coluna
        slots_with_distance = []
        for slot in free_slots:
            dist = DistanceService.calculate_distance(current_slot, slot)
            d_col = abs(current_slot.col_index - slot.col_index)
            d_row = abs(current_slot.row_index - slot.row_index)
            # chave: distância, variação de coluna, variação de linha, coluna, linha
            key = (dist, d_col, d_row, slot.col_index, slot.row_index)
            slots_with_distance.append((slot, key))

        # Ordenar por distância com desempate determinístico
        slots_with_distance.sort(key=lambda x: x[1])
        return slots_with_distance[0][0]

    @staticmethod
    def assign_devices_auto(
        db: Session,
        device_ids: List[str],
        start_slot: Optional[Slot] = None
    ) -> dict:
        """
        Aloca automaticamente uma lista de devices em slots livres
        usando algoritmo guloso (sempre ao slot livre mais próximo)

        Retorna:
            {
                "assigned": [{device_id, slot_id, human_code}],
                "failed": [device_id],
                "current_position": {slot_id, human_code}
            }
        """
        if not device_ids:
            return {"assigned": [], "failed": [], "current_position": None}

        # Usar slot de início dinâmico (último movimento) se não fornecido
        if start_slot is None:
            start_slot = AssignmentService.get_dynamic_start_slot(db)

        if not start_slot:
            return {
                "assigned": [],
                "failed": device_ids,
                "current_position": None,
                "error": "Nenhum slot disponível para alocação"
            }

        assigned = []
        failed = []
        current_position = start_slot

        # Transação para garantir atomicidade
        try:
            for device_id in device_ids:
                # Encontrar slot livre mais próximo
                nearest_slot = AssignmentService.find_nearest_free_slot(
                    db, current_position
                )

                if not nearest_slot:
                    failed.append(device_id)
                    continue

                # Buscar ou criar device
                device = db.query(Device).filter(
                    Device.device_id == device_id
                ).first()

                if not device:
                    device = Device(
                        device_id=device_id,
                        status=DeviceStatus.IN_STOCK,
                        slot_id=nearest_slot.id
                    )
                    db.add(device)
                else:
                    # Se device já está em um slot, liberar o slot anterior
                    if device.slot_id and device.slot_id != nearest_slot.id:
                        old_slot = db.query(Slot).filter(
                            Slot.id == device.slot_id
                        ).first()
                        if old_slot:
                            old_slot.occupied = False

                    device.status = DeviceStatus.IN_STOCK
                    device.slot_id = nearest_slot.id

                # Marcar slot como ocupado
                nearest_slot.occupied = True

                # Registrar movimento
                movement = Movement(
                    device_id=device_id,
                    from_slot_id=None,  # Alocação nova
                    to_slot_id=nearest_slot.id,
                    type=MovementType.CHECK_IN,
                    meta_json={"auto_assigned": True}
                )
                db.add(movement)

                # Flush para garantir que o próximo find_nearest_free_slot veja esta alocação
                db.flush()

                assigned.append({
                    "device_id": device_id,
                    "slot_id": nearest_slot.id,
                    "human_code": nearest_slot.human_code,
                    "row": nearest_slot.row_index,
                    "col": nearest_slot.col_index
                })

                # Atualizar posição atual para o próximo device
                current_position = nearest_slot

            db.commit()

            final_position = {
                "slot_id": current_position.id,
                "human_code": current_position.human_code
            }

            return {
                "assigned": assigned,
                "failed": failed,
                "current_position": final_position
            }

        except Exception as e:
            db.rollback()
            raise Exception(f"Erro ao alocar devices: {str(e)}")

