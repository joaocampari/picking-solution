"""
Serviço para cálculo de ordem de picking (coleta)
usando Nearest Neighbor + 2-opt simples
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.slot import Slot
from models.device import Device, DeviceStatus
from models.movement import Movement, MovementType
from services.distance_service import DistanceService
from typing import List, Dict, Optional, Tuple
import random
import time


class PickingService:
    """Gerencia planejamento e execução de picking"""

    @staticmethod
    def get_device_slots(
        db: Session,
        device_ids: List[str]
    ) -> Dict[str, Slot]:
        """
        Mapeia device_ids para seus slots atuais (apenas IN_STOCK)
        """
        devices = db.query(Device).filter(
            Device.device_id.in_(device_ids),
            Device.status == DeviceStatus.IN_STOCK,
            Device.slot_id.isnot(None)
        ).all()

        # Buscar slots
        slot_ids = [d.slot_id for d in devices if d.slot_id]
        slots = db.query(Slot).filter(Slot.id.in_(slot_ids)).all()
        slot_dict = {s.id: s for s in slots}

        # Criar mapeamento device_id -> slot
        device_slot_map = {}
        for device in devices:
            if device.slot_id and device.slot_id in slot_dict:
                device_slot_map[device.device_id] = slot_dict[device.slot_id]

        return device_slot_map

    @staticmethod
    def nearest_neighbor_route(
        start_slot: Slot,
        target_slots: List[Slot]
    ) -> List[Slot]:
        """
        Constrói rota usando Nearest Neighbor (vizinho mais próximo)
        Critério: menor distância; em empates, prioriza menor variação de linha,
        depois menor variação de coluna, e por fim linha/coluna menores.
        """
        if not target_slots:
            return []

        route = []
        unvisited = target_slots.copy()
        current = start_slot

        while unvisited:
            # Encontrar slot não visitado mais próximo com desempate determinístico
            best_slot = None
            best_key = None

            for slot in unvisited:
                dist = DistanceService.calculate_distance(current, slot)
                d_row = abs(current.row_index - slot.row_index)
                d_col = abs(current.col_index - slot.col_index)
                # Preferir mesma coluna primeiro; chave: distância, variação de coluna, variação de linha, coluna, linha
                key = (dist, d_col, d_row, slot.col_index, slot.row_index)
                if best_key is None or key < best_key:
                    best_key = key
                    best_slot = slot

            if best_slot:
                route.append(best_slot)
                unvisited.remove(best_slot)
                current = best_slot

        return route

    @staticmethod
    def two_opt_improve(
        route: List[Slot],
        max_iterations: int = 200,
        max_time_sec: float = 2.0
    ) -> List[Slot]:
        """
        Melhora rota usando algoritmo 2-opt simples
        Tenta inverter segmentos da rota para reduzir distância total
        """
        if len(route) < 3:
            return route

        best_route = route.copy()
        best_distance = PickingService._route_distance(best_route)

        start_time = time.time()
        improved = True
        iterations = 0

        while improved and iterations < max_iterations:
            if time.time() - start_time > max_time_sec:
                break

            improved = False
            iterations += 1

            for i in range(1, len(best_route) - 1):
                for j in range(i + 1, len(best_route)):
                    # Tentar inverter segmento [i:j]
                    new_route = best_route[:i] + best_route[i:j+1][::-1] + best_route[j+1:]
                    new_distance = PickingService._route_distance(new_route)

                    if new_distance < best_distance:
                        best_route = new_route
                        best_distance = new_distance
                        improved = True
                        break

                if improved:
                    break

        return best_route

    @staticmethod
    def _route_distance(route: List[Slot]) -> float:
        """Calcula distância total de uma rota"""
        if len(route) < 2:
            return 0.0

        total = 0.0
        for i in range(len(route) - 1):
            total += DistanceService.calculate_distance(route[i], route[i + 1])

        return total

    @staticmethod
    def create_picking_plan(
        db: Session,
        device_ids: List[str],
        start_slot: Optional[Slot] = None
    ) -> dict:
        """
        Cria plano de picking usando Nearest Neighbor + 2-opt

        Retorna:
            {
                "route": [
                    {
                        "device_id": str,
                        "slot_id": int,
                        "human_code": str,
                        "row": int,
                        "col": int,
                        "distance_from_prev": float,
                        "cumulative_distance": float
                    }
                ],
                "total_distance": float,
                "start_position": {slot_id, human_code}
            }
        """
        from services.assignment_service import AssignmentService

        # Usar slot de início padrão se não fornecido
        if start_slot is None:
            start_slot = AssignmentService.get_default_start_slot(db)

        if not start_slot:
            return {
                "route": [],
                "total_distance": 0.0,
                "start_position": None,
                "error": "Slot de início não encontrado"
            }

        # Mapear devices para slots
        device_slot_map = PickingService.get_device_slots(db, device_ids)

        # Filtrar apenas devices que estão em slots
        valid_devices = [
            did for did in device_ids
            if did in device_slot_map
        ]

        if not valid_devices:
            return {
                "route": [],
                "total_distance": 0.0,
                "start_position": {
                    "slot_id": start_slot.id,
                    "human_code": start_slot.human_code
                },
                "error": "Nenhum device encontrado em estoque"
            }

        # Extrair slots alvo
        target_slots = [device_slot_map[did] for did in valid_devices]

        # Construir rota com Nearest Neighbor
        route_slots = PickingService.nearest_neighbor_route(
            start_slot, target_slots
        )

        # Melhorar rota com 2-opt
        route_slots = PickingService.two_opt_improve(route_slots)

        # Construir resposta com informações completas
        route_result = []
        cumulative_distance = 0.0
        previous_slot = start_slot

        for slot in route_slots:
            # Encontrar device_id correspondente a este slot
            device_id = None
            for did, s in device_slot_map.items():
                if s.id == slot.id:
                    device_id = did
                    break

            if device_id:
                distance_from_prev = DistanceService.calculate_distance(
                    previous_slot, slot
                )
                cumulative_distance += distance_from_prev

                route_result.append({
                    "device_id": device_id,
                    "slot_id": slot.id,
                    "human_code": slot.human_code,
                    "row": slot.row_index,
                    "col": slot.col_index,
                    "distance_from_prev": distance_from_prev,
                    "cumulative_distance": cumulative_distance
                })

                previous_slot = slot

        # Distância de retorno ao início (opcional, para fechar o ciclo)
        return_distance = DistanceService.calculate_distance(
            previous_slot, start_slot
        )
        total_distance = cumulative_distance

        return {
            "route": route_result,
            "total_distance": total_distance,
            "return_distance": return_distance,
            "start_position": {
                "slot_id": start_slot.id,
                "human_code": start_slot.human_code
            }
        }

    @staticmethod
    def mark_device_in_transit(
        db: Session,
        device_id: str
    ) -> dict:
        """
        Marca um device como em trânsito (IN_TRANSIT) ao iniciar a coleta.
        Não libera o slot ainda.
        """
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            return {"success": False, "error": f"Device {device_id} não encontrado"}
        if device.status not in (DeviceStatus.IN_STOCK, DeviceStatus.IN_TRANSIT):
            return {"success": False, "error": f"Device {device_id} não está disponível para coleta"}
        try:
            device.status = DeviceStatus.IN_TRANSIT
            movement = Movement(
                device_id=device_id,
                from_slot_id=device.slot_id,
                to_slot_id=device.slot_id,
                type=MovementType.MOVE,
                meta_json={"in_transit": True}
            )
            db.add(movement)
            db.commit()
            return {"success": True}
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}

    @staticmethod
    def mark_device_picked(
        db: Session,
        device_id: str
    ) -> dict:
        """
        Marca um device como coletado (picked)
        Libera o slot e registra movimento
        """
        device = db.query(Device).filter(
            Device.device_id == device_id
        ).first()

        if not device:
            return {
                "success": False,
                "error": f"Device {device_id} não encontrado"
            }

        if device.status not in (DeviceStatus.IN_STOCK, DeviceStatus.IN_TRANSIT):
            return {
                "success": False,
                "error": f"Device {device_id} não está em coleta"
            }

        if not device.slot_id:
            return {
                "success": False,
                "error": f"Device {device_id} não está alocado em nenhum slot"
            }

        # Buscar slot
        slot = db.query(Slot).filter(Slot.id == device.slot_id).first()

        try:
            # Liberar slot
            if slot:
                slot.occupied = False

            # Atualizar device
            old_slot_id = device.slot_id
            device.slot_id = None
            device.status = DeviceStatus.OUT_STOCK

            # Registrar movimento
            movement = Movement(
                device_id=device_id,
                from_slot_id=old_slot_id,
                to_slot_id=None,
                type=MovementType.CHECK_OUT,
                meta_json={"picked": True}
            )
            db.add(movement)

            db.commit()

            return {
                "success": True,
                "device_id": device_id,
                "slot_freed": old_slot_id,
                "human_code": slot.human_code if slot else None
            }

        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "error": f"Erro ao marcar device como coletado: {str(e)}"
            }

    @staticmethod
    def mark_devices_in_transit(
        db: Session,
        device_ids: List[str]
    ) -> dict:
        """Marca todos os devices da lista como IN_TRANSIT (se estiverem IN_STOCK)."""
        updated = 0
        try:
            devices = db.query(Device).filter(Device.device_id.in_(device_ids)).all()
            for d in devices:
                if d.status == DeviceStatus.IN_STOCK:
                    d.status = DeviceStatus.IN_TRANSIT
                    mv = Movement(
                        device_id=d.device_id,
                        from_slot_id=d.slot_id,
                        to_slot_id=d.slot_id,
                        type=MovementType.MOVE,
                        meta_json={"in_transit": True, "bulk_plan": True}
                    )
                    db.add(mv)
                    updated += 1
            db.commit()
            return {"success": True, "updated": updated}
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}

    @staticmethod
    def reset_devices_from_transit(
        db: Session,
        device_ids: List[str]
    ) -> dict:
        """Cancela plano: volta devices IN_TRANSIT para IN_STOCK sem liberar slot."""
        updated = 0
        try:
            devices = db.query(Device).filter(Device.device_id.in_(device_ids)).all()
            for d in devices:
                if d.status == DeviceStatus.IN_TRANSIT:
                    d.status = DeviceStatus.IN_STOCK
                    mv = Movement(
                        device_id=d.device_id,
                        from_slot_id=d.slot_id,
                        to_slot_id=d.slot_id,
                        type=MovementType.RELEASE,
                        meta_json={"cancel_plan": True}
                    )
                    db.add(mv)
                    updated += 1
            db.commit()
            return {"success": True, "updated": updated}
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}

