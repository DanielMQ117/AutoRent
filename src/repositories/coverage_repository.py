"""Repositorio de acceso a datos para Coberturas de Seguro (DAL)."""

from decimal import Decimal
from typing import Any, List, Optional

from src.core.logger import get_logger
from src.domain.models import InsuranceCoverage
from src.repositories.base_repository import BaseRepository

logger = get_logger(__name__)


class CoverageRepository(BaseRepository[InsuranceCoverage]):
    """Operaciones de persistencia para el catálogo de coberturas de seguro."""

    @staticmethod
    def _map_row_to_coverage(row: dict) -> InsuranceCoverage:
        """Convierte un registro relacional en una entidad InsuranceCoverage."""
        return InsuranceCoverage(
            id_cobertura=row["id_cobertura"],
            tenant_id=row["tenant_id"],
            nombre=row["nombre"],
            descripcion=row["descripcion"],
            costo_diario=Decimal(str(row["costo_diario"])),
            porcentaje_deducible=Decimal(str(row["porcentaje_deducible"])),
        )

    def list_all(self, conn: Any = None) -> List[InsuranceCoverage]:
        """Retorna todas las pólizas/coberturas de seguro disponibles en la agencia activa ordenadas por costo."""
        query = """
            SELECT id_cobertura, tenant_id, nombre, descripcion, costo_diario, porcentaje_deducible
            FROM coberturas_seguro
            WHERE tenant_id = %s
            ORDER BY costo_diario ASC;
        """
        rows = self.execute_query(query, (self.current_tenant_id,), conn=conn)
        return [self._map_row_to_coverage(r) for r in rows]

    def get_by_id(self, id_cobertura: int, conn: Any = None) -> Optional[InsuranceCoverage]:
        """Obtiene una cobertura específica por su identificador primario dentro de la agencia activa."""
        query = """
            SELECT id_cobertura, tenant_id, nombre, descripcion, costo_diario, porcentaje_deducible
            FROM coberturas_seguro
            WHERE id_cobertura = %s AND tenant_id = %s;
        """
        row = self.execute_query_one(query, (id_cobertura, self.current_tenant_id), conn=conn)
        return self._map_row_to_coverage(row) if row else None
