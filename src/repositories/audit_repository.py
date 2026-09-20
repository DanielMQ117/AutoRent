"""Repositorio de acceso a datos para la Bitácora de Auditoría (RF-05).

Garantiza la inmutabilidad de los registros de auditoría (únicamente operaciones de inserción y lectura).
"""

from typing import Any, List, Optional
from src.domain.models import AuditLog
from src.repositories.base_repository import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    """Operaciones de persistencia inmutable para la bitácora de auditoría y seguridad."""

    @staticmethod
    def _map_row_to_audit(row: dict) -> AuditLog:
        """Mapea una fila de base de datos a un objeto de dominio AuditLog."""
        return AuditLog(
            id_auditoria=row["id_auditoria"],
            id_usuario=row.get("id_usuario"),
            username=row["username"],
            accion=row["accion"],
            tabla_afectada=row["tabla_afectada"],
            id_registro=row.get("id_registro"),
            detalles=row.get("detalles"),
            ip_origen=row.get("ip_origen", "127.0.0.1"),
            fecha_registro=row.get("fecha_registro"),
        )

    def record_action(
        self,
        id_usuario: Optional[int],
        username: str,
        accion: str,
        tabla_afectada: str,
        id_registro: Optional[int] = None,
        detalles: Optional[str] = None,
        ip_origen: str = "127.0.0.1",
        conn: Any = None,
    ) -> int:
        """Inserta un nuevo registro inmutable en la bitácora de auditoría."""
        query = """
            INSERT INTO auditoria (
                id_usuario, username, accion, tabla_afectada, id_registro, detalles, ip_origen
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id_auditoria;
        """
        params = (
            id_usuario,
            username.strip(),
            accion.strip().upper(),
            tabla_afectada.strip().lower(),
            id_registro,
            detalles,
            ip_origen,
        )
        row = self.execute_query_one(query, params, conn=conn)
        return int(row["id_auditoria"]) if row else 0

    def list_logs(
        self,
        limit: int = 150,
        accion: Optional[str] = None,
        username: Optional[str] = None,
        tabla_afectada: Optional[str] = None,
    ) -> List[AuditLog]:
        """Consulta los eventos de auditoría más recientes con filtros opcionales."""
        query = """
            SELECT 
                id_auditoria,
                id_usuario,
                username,
                accion,
                tabla_afectada,
                id_registro,
                detalles,
                ip_origen,
                fecha_registro
            FROM auditoria
            WHERE 1=1
        """
        params: list[Any] = []

        if accion:
            query += " AND accion = %s"
            params.append(accion.strip().upper())

        if username:
            query += " AND (username ILIKE %s)"
            params.append(f"%{username.strip()}%")

        if tabla_afectada:
            query += " AND tabla_afectada = %s"
            params.append(tabla_afectada.strip().lower())

        query += " ORDER BY id_auditoria DESC LIMIT %s;"
        params.append(limit)

        rows = self.execute_query(query, tuple(params))
        return [self._map_row_to_audit(r) for r in rows]

    def count_total_logs(self) -> int:
        """Retorna la cantidad total de eventos registrados en la bitácora."""
        query = "SELECT COUNT(*) FROM auditoria;"
        return int(self.execute_scalar(query) or 0)
