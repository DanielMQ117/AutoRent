"""Repositorio de acceso a datos para Mantenimiento de Flota y Taller Mecánico (DAL)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional

from src.core.logger import get_logger
from src.domain.enums import MaintenanceStatus, MaintenanceType
from src.domain.models import Maintenance
from src.repositories.base_repository import BaseRepository

logger = get_logger(__name__)


class MaintenanceRepository(BaseRepository[Maintenance]):
    """Operaciones de persistencia para órdenes de taller preventivo y correctivo."""

    @staticmethod
    def _map_row_to_maintenance(row: dict) -> Maintenance:
        """Mapea una fila relacional con JOINs a un objeto de dominio Maintenance."""
        return Maintenance(
            id_mantenimiento=row["id_mantenimiento"],
            id_vehiculo=row["id_vehiculo"],
            tipo_mantenimiento=MaintenanceType(row["tipo_mantenimiento"]),
            fecha_ingreso=row["fecha_ingreso"],
            fecha_salida_estimada=row["fecha_salida_estimada"],
            fecha_salida_real=row.get("fecha_salida_real"),
            kilometraje_entrada=row["kilometraje_entrada"],
            taller_servicio=row["taller_servicio"],
            descripcion_trabajo=row["descripcion_trabajo"],
            costo_total=Decimal(str(row["costo_total"])),
            estado=MaintenanceStatus(row["estado"]),
            id_usuario=row["id_usuario"],
            vehiculo_placa=row.get("vehiculo_placa"),
            vehiculo_modelo=row.get("vehiculo_modelo"),
            vehiculo_categoria=row.get("vehiculo_categoria"),
            vehiculo_kilometraje_actual=row.get("vehiculo_kilometraje_actual", 0),
            km_proximo_mantenimiento_actual=row.get("km_proximo_mantenimiento_actual", 0),
            usuario_nombre=row.get("usuario_nombre"),
        )

    def create(self, maintenance: Maintenance, conn: Any = None) -> Maintenance:
        """Inserta una nueva orden de servicio en taller en la base de datos."""
        query = """
            INSERT INTO mantenimientos (
                id_vehiculo,
                tipo_mantenimiento,
                fecha_ingreso,
                fecha_salida_estimada,
                kilometraje_entrada,
                taller_servicio,
                descripcion_trabajo,
                costo_total,
                estado,
                id_usuario
            ) VALUES (
                %(id_vehiculo)s,
                %(tipo_mantenimiento)s,
                %(fecha_ingreso)s,
                %(fecha_salida_estimada)s,
                %(kilometraje_entrada)s,
                %(taller_servicio)s,
                %(descripcion_trabajo)s,
                %(costo_total)s,
                %(estado)s,
                %(id_usuario)s
            ) RETURNING id_mantenimiento;
        """
        params = {
            "id_vehiculo": maintenance.id_vehiculo,
            "tipo_mantenimiento": maintenance.tipo_mantenimiento.value if hasattr(maintenance.tipo_mantenimiento, "value") else str(maintenance.tipo_mantenimiento),
            "fecha_ingreso": maintenance.fecha_ingreso or datetime.now(),
            "fecha_salida_estimada": maintenance.fecha_salida_estimada or date.today(),
            "kilometraje_entrada": maintenance.kilometraje_entrada,
            "taller_servicio": maintenance.taller_servicio,
            "descripcion_trabajo": maintenance.descripcion_trabajo,
            "costo_total": maintenance.costo_total,
            "estado": maintenance.estado.value if hasattr(maintenance.estado, "value") else str(maintenance.estado),
            "id_usuario": maintenance.id_usuario,
        }

        created_id = self.execute_scalar(query, params, conn=conn)
        maintenance.id_mantenimiento = created_id
        logger.info(
            "Orden de mantenimiento ID %s registrada para vehículo ID %s (%s).",
            created_id,
            maintenance.id_vehiculo,
            maintenance.tipo_mantenimiento,
        )
        return maintenance

    def complete(
        self,
        id_mantenimiento: int,
        fecha_salida_real: datetime,
        costo_total: Decimal,
        descripcion_adicional: Optional[str] = None,
        conn: Any = None,
    ) -> bool:
        """Marca una orden de mantenimiento como FINALIZADA con fecha real y costo total auditado."""
        query = """
            UPDATE mantenimientos
            SET estado = 'FINALIZADO',
                fecha_salida_real = %s,
                costo_total = %s,
                descripcion_trabajo = CASE 
                    WHEN %s IS NOT NULL AND %s <> '' 
                    THEN descripcion_trabajo || ' | Trabajos finales: ' || %s
                    ELSE descripcion_trabajo
                END
            WHERE id_mantenimiento = %s;
        """
        desc_txt = descripcion_adicional or ""
        rows = self.execute_non_query(
            query,
            (fecha_salida_real, costo_total, desc_txt, desc_txt, desc_txt, id_mantenimiento),
            conn=conn,
        )
        return rows > 0

    def cancel(self, id_mantenimiento: int, motivo: Optional[str] = None, conn: Any = None) -> bool:
        """Marca una orden de mantenimiento como CANCELADA."""
        query = """
            UPDATE mantenimientos
            SET estado = 'CANCELADO',
                descripcion_trabajo = CASE 
                    WHEN %s IS NOT NULL AND %s <> '' 
                    THEN descripcion_trabajo || ' [Motivo cancelación: ' || %s || ']'
                    ELSE descripcion_trabajo
                END
            WHERE id_mantenimiento = %s;
        """
        motivo_txt = motivo or ""
        rows = self.execute_non_query(
            query,
            (motivo_txt, motivo_txt, motivo_txt, id_mantenimiento),
            conn=conn,
        )
        return rows > 0

    def get_by_id(self, id_mantenimiento: int, conn: Any = None) -> Optional[Maintenance]:
        """Obtiene una orden de mantenimiento por su ID primario con datos relacionales completos."""
        query = """
            SELECT 
                m.id_mantenimiento,
                m.id_vehiculo,
                m.tipo_mantenimiento,
                m.fecha_ingreso,
                m.fecha_salida_estimada,
                m.fecha_salida_real,
                m.kilometraje_entrada,
                m.taller_servicio,
                m.descripcion_trabajo,
                m.costo_total,
                m.estado,
                m.id_usuario,
                v.placa AS vehiculo_placa,
                (ma.nombre || ' ' || mo.nombre) AS vehiculo_modelo,
                c.nombre AS vehiculo_categoria,
                v.kilometraje_actual AS vehiculo_kilometraje_actual,
                v.km_proximo_mantenimiento AS km_proximo_mantenimiento_actual,
                u.nombre_completo AS usuario_nombre
            FROM mantenimientos m
            INNER JOIN vehiculos v ON m.id_vehiculo = v.id_vehiculo
            INNER JOIN modelos mo ON v.id_modelo = mo.id_modelo
            INNER JOIN marcas ma ON mo.id_marca = ma.id_marca
            INNER JOIN categorias_vehiculo c ON v.id_categoria = c.id_categoria
            INNER JOIN usuarios u ON m.id_usuario = u.id_usuario
            WHERE m.id_mantenimiento = %s;
        """
        row = self.execute_query_one(query, (id_mantenimiento,), conn=conn)
        return self._map_row_to_maintenance(row) if row else None

    def get_active_by_vehicle(self, id_vehiculo: int, conn: Any = None) -> Optional[Maintenance]:
        """Obtiene la orden activa en taller de un vehículo si existe."""
        query = """
            SELECT 
                m.id_mantenimiento,
                m.id_vehiculo,
                m.tipo_mantenimiento,
                m.fecha_ingreso,
                m.fecha_salida_estimada,
                m.fecha_salida_real,
                m.kilometraje_entrada,
                m.taller_servicio,
                m.descripcion_trabajo,
                m.costo_total,
                m.estado,
                m.id_usuario,
                v.placa AS vehiculo_placa,
                (ma.nombre || ' ' || mo.nombre) AS vehiculo_modelo,
                c.nombre AS vehiculo_categoria,
                v.kilometraje_actual AS vehiculo_kilometraje_actual,
                v.km_proximo_mantenimiento AS km_proximo_mantenimiento_actual,
                u.nombre_completo AS usuario_nombre
            FROM mantenimientos m
            INNER JOIN vehiculos v ON m.id_vehiculo = v.id_vehiculo
            INNER JOIN modelos mo ON v.id_modelo = mo.id_modelo
            INNER JOIN marcas ma ON mo.id_marca = ma.id_marca
            INNER JOIN categorias_vehiculo c ON v.id_categoria = c.id_categoria
            INNER JOIN usuarios u ON m.id_usuario = u.id_usuario
            WHERE m.id_vehiculo = %s AND m.estado = 'EN_TALLER'
            ORDER BY m.id_mantenimiento DESC
            LIMIT 1;
        """
        row = self.execute_query_one(query, (id_vehiculo,), conn=conn)
        return self._map_row_to_maintenance(row) if row else None

    def list_all(
        self,
        search: str = "",
        status: Optional[str] = None,
        maintenance_type: Optional[str] = None,
        vehicle_id: Optional[int] = None,
        limit: int = 100,
        conn: Any = None,
    ) -> List[Maintenance]:
        """Lista las órdenes de mantenimiento registradas aplicando filtros opcionales."""
        query = """
            SELECT 
                m.id_mantenimiento,
                m.id_vehiculo,
                m.tipo_mantenimiento,
                m.fecha_ingreso,
                m.fecha_salida_estimada,
                m.fecha_salida_real,
                m.kilometraje_entrada,
                m.taller_servicio,
                m.descripcion_trabajo,
                m.costo_total,
                m.estado,
                m.id_usuario,
                v.placa AS vehiculo_placa,
                (ma.nombre || ' ' || mo.nombre) AS vehiculo_modelo,
                c.nombre AS vehiculo_categoria,
                v.kilometraje_actual AS vehiculo_kilometraje_actual,
                v.km_proximo_mantenimiento AS km_proximo_mantenimiento_actual,
                u.nombre_completo AS usuario_nombre
            FROM mantenimientos m
            INNER JOIN vehiculos v ON m.id_vehiculo = v.id_vehiculo
            INNER JOIN modelos mo ON v.id_modelo = mo.id_modelo
            INNER JOIN marcas ma ON mo.id_marca = ma.id_marca
            INNER JOIN categorias_vehiculo c ON v.id_categoria = c.id_categoria
            INNER JOIN usuarios u ON m.id_usuario = u.id_usuario
            WHERE 1=1
        """
        params: list[Any] = []

        if search:
            query += """
                AND (
                    v.placa ILIKE %s
                    OR ma.nombre ILIKE %s
                    OR mo.nombre ILIKE %s
                    OR m.taller_servicio ILIKE %s
                    OR m.descripcion_trabajo ILIKE %s
                )
            """
            s_term = f"%{search.strip()}%"
            params.extend([s_term, s_term, s_term, s_term, s_term])

        if status and status != "TODOS":
            query += " AND m.estado = %s"
            params.append(status)

        if maintenance_type and maintenance_type != "TODOS":
            query += " AND m.tipo_mantenimiento = %s"
            params.append(maintenance_type)

        if vehicle_id:
            query += " AND m.id_vehiculo = %s"
            params.append(vehicle_id)

        query += " ORDER BY m.id_mantenimiento DESC LIMIT %s;"
        params.append(limit)

        rows = self.execute_query(query, tuple(params), conn=conn)
        return [self._map_row_to_maintenance(r) for r in rows]

    def count_maintenances(self, status: Optional[str] = None, conn: Any = None) -> int:
        """Retorna el número total de órdenes de taller, opcionalmente filtradas por estado."""
        if status:
            query = "SELECT COUNT(*) FROM mantenimientos WHERE estado = %s;"
            return int(self.execute_scalar(query, (status,), conn=conn) or 0)
        query = "SELECT COUNT(*) FROM mantenimientos;"
        return int(self.execute_scalar(query, conn=conn) or 0)

    def get_total_expenses(self, conn: Any = None) -> Decimal:
        """Retorna la sumatoria económica invertida en mantenimiento y taller."""
        query = "SELECT COALESCE(SUM(costo_total), 0) FROM mantenimientos WHERE estado = 'FINALIZADO';"
        val = self.execute_scalar(query, conn=conn)
        return Decimal(str(val or 0.00))
