"""
Serviço para cálculo de distância Manhattan entre slots
com custos configuráveis por mudança de rua/prateleira
"""
import os
from dotenv import load_dotenv

load_dotenv()


class DistanceService:
    """Calcula distância Manhattan entre slots com custos configuráveis"""

    # Custos padrão (podem ser sobrescritos via .env)
    CUSTO_MUDAR_RUA = int(os.getenv("CUSTO_MUDAR_RUA", "10"))
    CUSTO_MUDAR_PRATELEIRA = int(os.getenv("CUSTO_MUDAR_PRATELEIRA", "5"))
    CUSTO_POR_LINHA = int(os.getenv("CUSTO_POR_LINHA", "1"))
    CUSTO_POR_COLUNA = int(os.getenv("CUSTO_POR_COLUNA", "1"))

    @staticmethod
    def calculate_distance(slot1, slot2):
        """
        Calcula distância Manhattan entre dois slots com custos:
        - Custo por trocar de rua
        - Custo por trocar de prateleira
        - Custo por linha (diferença de linhas)
        - Custo por coluna (diferença de colunas)
        """
        # Se for o mesmo slot, distância é 0
        if slot1.id == slot2.id:
            return 0

        cost = 0

        # Custo por trocar de rua
        if slot1.aisle_id != slot2.aisle_id:
            cost += DistanceService.CUSTO_MUDAR_RUA

        # Custo por trocar de prateleira (mesmo que na mesma rua)
        if slot1.shelf_id != slot2.shelf_id:
            cost += DistanceService.CUSTO_MUDAR_PRATELEIRA

        # Custo por diferença de linhas
        line_diff = abs(slot1.row_index - slot2.row_index)
        cost += line_diff * DistanceService.CUSTO_POR_LINHA

        # Custo por diferença de colunas
        col_diff = abs(slot1.col_index - slot2.col_index)
        cost += col_diff * DistanceService.CUSTO_POR_COLUNA

        return cost

    @staticmethod
    def calculate_distance_from_coords(
        aisle_id_1, shelf_id_1, row_1, col_1,
        aisle_id_2, shelf_id_2, row_2, col_2
    ):
        """
        Calcula distância a partir de coordenadas (útil quando não tem objetos Slot)
        """
        cost = 0

        if aisle_id_1 != aisle_id_2:
            cost += DistanceService.CUSTO_MUDAR_RUA

        if shelf_id_1 != shelf_id_2:
            cost += DistanceService.CUSTO_MUDAR_PRATELEIRA

        line_diff = abs(row_1 - row_2)
        cost += line_diff * DistanceService.CUSTO_POR_LINHA

        col_diff = abs(col_1 - col_2)
        cost += col_diff * DistanceService.CUSTO_POR_COLUNA

        return cost

