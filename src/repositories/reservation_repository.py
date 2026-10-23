"""Repositorio de acceso a datos para la entidad Reserva y Disponibilidad Temporal (DAL)."""

from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional
from src.core.logger import get_logger
from src.domain.enums import ReservationStatus, VehicleStatus
from src.domain.models import Reservation, Vehicle
from src.repositories.base_repository import BaseRepository

logger = get_logger(__name__)


class ReservationRepository(BaseRepository[Reservation]):
    """Operaciones de persistencia para la gestión integral de reservas y control de disponibilidad."""

    @staticmethod
    def _map_row_to_reservation(row: dict) -> Reservation:
        """Mapea una fila relacional con JOINs a un objeto de dominio Reservation."""
        return Reservation(
            id_reserva=row["id_reserva"],
            tenant_id=row.get("tenant_id", 1),
            codigo_reserva=row["codigo_reserva"],
            id_cliente=row["id_cliente"],
            id_categoria=row["id_categoria"],
            id_vehiculo=row.get("id_vehiculo"),
            fecha_hora_inicio=row["fecha_hora_inicio"],
            fecha_hora_fin=row["fecha_hora_fin"],
            monto_anticipo=Decimal(str(row["monto_anticipo"])),
            estado=ReservationStatus(row["estado"]),
            id_usuario=row["id_usuario"],
            fecha_creacion=row.get("fecha_creacion"),
            cliente_nombre=row.get("cliente_nombre"),
            cliente_identificacion=row.get("cliente_identificacion"),
            categoria_nombre=row.get("categoria_nombre"),
            tarifa_base_diaria=Decimal(str(row["tarifa_base_diaria"])) if row.get("tarifa_base_diaria") is not None else None,
            vehiculo_placa=row.get("vehiculo_placa"),
            vehiculo_modelo=row.get("vehiculo_modelo"),
            usuario_nombre=row.get("usuario_nombre"),
        )

    def get_by_id(self, id_reserva: int, conn: Any = None) -> Optional[Reservation]:
        """Obtiene una reserva por su ID primario con detalles de cliente, categoría y vehículo."""
        query = """
            SELECT 
                r.id_reserva,
                r.tenant_id,
                r.codigo_reserva,
                r.id_cliente,
                r.id_categoria,
                r.id_vehiculo,
                r.fecha_hora_inicio,
                r.fecha_hora_fin,
                r.monto_anticipo,
                r.estado,
                r.id_usuario,
                r.fecha_creacion,
                (c.nombres || ' ' || c.apellidos) AS cliente_nombre,
                c.identificacion AS cliente_identificacion,
                cat.nombre AS categoria_nombre,
                cat.tarifa_base_diaria AS tarifa_base_diaria,
                v.placa AS vehiculo_placa,
                (mar.nombre || ' ' || m.nombre) AS vehiculo_modelo,
                u.nombre_completo AS usuario_nombre
            FROM reservas r
            INNER JOIN clientes c ON r.id_cliente = c.id_cliente
            INNER JOIN categorias_vehiculo cat ON r.id_categoria = cat.id_categoria
            LEFT JOIN vehiculos v ON r.id_vehiculo = v.id_vehiculo
            LEFT JOIN modelos m ON v.id_modelo = m.id_modelo
            LEFT JOIN marcas mar ON m.id_marca = mar.id_marca
            INNER JOIN usuarios u ON r.id_usuario = u.id_usuario
            WHERE r.id_reserva = %s AND r.tenant_id = %s;
        """
        row = self.execute_query_one(query, (id_reserva, self.current_tenant_id), conn=conn)
        return self._map_row_to_reservation(row) if row else None

    def get_by_codigo(self, codigo: str, conn: Any = None) -> Optional[Reservation]:
        """Obtiene una reserva por su código alfanumérico único dentro de la agencia activa."""
        query = """
            SELECT 
                r.id_reserva,
                r.tenant_id,
                r.codigo_reserva,
                r.id_cliente,
                r.id_categoria,
                r.id_vehiculo,
                r.fecha_hora_inicio,
                r.fecha_hora_fin,
                r.monto_anticipo,
                r.estado,
                r.id_usuario,
                r.fecha_creacion,
                (c.nombres || ' ' || c.apellidos) AS cliente_nombre,
                c.identificacion AS cliente_identificacion,
                cat.nombre AS categoria_nombre,
                cat.tarifa_base_diaria AS tarifa_base_diaria,
                v.placa AS vehiculo_placa,
                (mar.nombre || ' ' || m.nombre) AS vehiculo_modelo,
                u.nombre_completo AS usuario_nombre
            FROM reservas r
            INNER JOIN clientes c ON r.id_cliente = c.id_cliente
            INNER JOIN categorias_vehiculo cat ON r.id_categoria = cat.id_categoria
            LEFT JOIN vehiculos v ON r.id_vehiculo = v.id_vehiculo
            LEFT JOIN modelos m ON v.id_modelo = m.id_modelo
            LEFT JOIN marcas mar ON m.id_marca = mar.id_marca
            INNER JOIN usuarios u ON r.id_usuario = u.id_usuario
            WHERE UPPER(r.codigo_reserva) = UPPER(%s) AND r.tenant_id = %s;
        """
        row = self.execute_query_one(query, (codigo.strip(), self.current_tenant_id), conn=conn)
        return self._map_row_to_reservation(row) if row else None

    def list_all(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        client_id: Optional[int] = None,
        category_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        conn: Any = None,
    ) -> List[Reservation]:
        """Lista reservas de la agencia activa con soporte para filtros."""
        conditions = ["r.tenant_id = %s"]
        params: list[Any] = [self.current_tenant_id]

        if search and search.strip():
            term = f"%{search.strip()}%"
            conditions.append("""
                (r.codigo_reserva ILIKE %s 
                 OR c.nombres ILIKE %s 
                 OR c.apellidos ILIKE %s 
                 OR c.identificacion ILIKE %s 
                 OR v.placa ILIKE %s)
            """)
            params.extend([term, term, term, term, term])

        if status and status.strip() and status != "TODAS":
            conditions.append("r.estado = %s")
            params.append(status.strip())

        if client_id is not None:
            conditions.append("r.id_cliente = %s")
            params.append(client_id)

        if category_id is not None:
            conditions.append("r.id_categoria = %s")
            params.append(category_id)

        if from_date is not None:
            conditions.append("r.fecha_hora_inicio >= %s")
            params.append(from_date)

        if to_date is not None:
            conditions.append("r.fecha_hora_fin <= %s")
            params.append(to_date)

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT 
                r.id_reserva,
                r.tenant_id,
                r.codigo_reserva,
                r.id_cliente,
                r.id_categoria,
                r.id_vehiculo,
                r.fecha_hora_inicio,
                r.fecha_hora_fin,
                r.monto_anticipo,
                r.estado,
                r.id_usuario,
                r.fecha_creacion,
                (c.nombres || ' ' || c.apellidos) AS cliente_nombre,
                c.identificacion AS cliente_identificacion,
                cat.nombre AS categoria_nombre,
                cat.tarifa_base_diaria AS tarifa_base_diaria,
                v.placa AS vehiculo_placa,
                (mar.nombre || ' ' || m.nombre) AS vehiculo_modelo,
                u.nombre_completo AS usuario_nombre
            FROM reservas r
            INNER JOIN clientes c ON r.id_cliente = c.id_cliente
            INNER JOIN categorias_vehiculo cat ON r.id_categoria = cat.id_categoria
            LEFT JOIN vehiculos v ON r.id_vehiculo = v.id_vehiculo
            LEFT JOIN modelos m ON v.id_modelo = m.id_modelo
            LEFT JOIN marcas mar ON m.id_marca = mar.id_marca
            INNER JOIN usuarios u ON r.id_usuario = u.id_usuario
            WHERE {where_clause}
            ORDER BY r.fecha_hora_inicio DESC;
        """
        rows = self.execute_query(query, tuple(params), conn=conn)
        return [self._map_row_to_reservation(r) for r in rows]

    def create(self, reservation: Reservation, conn: Any = None) -> Reservation:
        """Inserta una nueva reserva en PostgreSQL y retorna la entidad con su ID generado."""
        target_tenant = self.current_tenant_id
        query = """
            INSERT INTO reservas (
                tenant_id,
                codigo_reserva,
                id_cliente,
                id_categoria,
                id_vehiculo,
                fecha_hora_inicio,
                fecha_hora_fin,
                monto_anticipo,
                estado,
                id_usuario
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_reserva, tenant_id, fecha_creacion;
        """
        params = (
            target_tenant,
            reservation.codigo_reserva,
            reservation.id_cliente,
            reservation.id_categoria,
            reservation.id_vehiculo,
            reservation.fecha_hora_inicio,
            reservation.fecha_hora_fin,
            reservation.monto_anticipo,
            reservation.estado.value,
            reservation.id_usuario,
        )
        row = self.execute_query_one(query, params, conn=conn)
        if not row:
            raise RuntimeError("Error al persistir la reserva: no se obtuvo fila de retorno.")

        reservation.id_reserva = row["id_reserva"]
        reservation.tenant_id = row["tenant_id"]
        reservation.fecha_creacion = row["fecha_creacion"]
        return reservation

    def update(self, reservation: Reservation, conn: Any = None) -> Reservation:
        """Actualiza los datos modificables de una reserva existente."""
        query = """
            UPDATE reservas
            SET 
                id_cliente = %s,
                id_categoria = %s,
                id_vehiculo = %s,
                fecha_hora_inicio = %s,
                fecha_hora_fin = %s,
                monto_anticipo = %s,
                estado = %s
            WHERE id_reserva = %s AND tenant_id = %s;
        """
        params = (
            reservation.id_cliente,
            reservation.id_categoria,
            reservation.id_vehiculo,
            reservation.fecha_hora_inicio,
            reservation.fecha_hora_fin,
            reservation.monto_anticipo,
            reservation.estado.value,
            reservation.id_reserva,
            self.current_tenant_id,
        )
        self.execute_non_query(query, params, conn=conn)
        return reservation

    def update_status(self, id_reserva: int, new_status: ReservationStatus, conn: Any = None) -> None:
        """Actualiza únicamente el estado de una reserva."""
        query = "UPDATE reservas SET estado = %s WHERE id_reserva = %s AND tenant_id = %s;"
        self.execute_non_query(query, (new_status.value, id_reserva, self.current_tenant_id), conn=conn)

    def check_vehicle_conflict(
        self,
        id_vehiculo: int,
        start_dt: datetime,
        end_dt: datetime,
        exclude_reservation_id: Optional[int] = None,
        conn: Any = None,
    ) -> bool:
        """Verifica si un vehículo específico presenta colisión de horario con reservas o contratos vigentes."""
        t_id = self.current_tenant_id
        query = """
            SELECT 1 FROM (
                -- 1. Colisión con reservas confirmadas o pendientes
                SELECT id_vehiculo FROM reservas
                WHERE id_vehiculo = %s
                  AND tenant_id = %s
                  AND estado IN ('CONFIRMADA', 'PENDIENTE')
                  AND (%s IS NULL OR id_reserva != %s)
                  AND tstzrange(fecha_hora_inicio, fecha_hora_fin, '[)') && tstzrange(%s, %s, '[)')
                
                UNION ALL
                
                -- 2. Colisión con contratos activos o en curso
                SELECT id_vehiculo FROM contratos
                WHERE id_vehiculo = %s
                  AND tenant_id = %s
                  AND estado IN ('ACTIVO', 'EN_INSPECCION', 'EN_LIQUIDACION')
                  AND tstzrange(fecha_hora_inicio_pactada, fecha_hora_fin_pactada, '[)') && tstzrange(%s, %s, '[)')
            ) AS conflictos
            LIMIT 1;
        """
        params = (
            id_vehiculo,
            t_id,
            exclude_reservation_id,
            exclude_reservation_id,
            start_dt,
            end_dt,
            id_vehiculo,
            t_id,
            start_dt,
            end_dt,
        )
        result = self.execute_query_one(query, params, conn=conn)
        return result is not None

    def get_available_vehicles_for_period(
        self,
        id_categoria: int,
        start_dt: datetime,
        end_dt: datetime,
        exclude_reservation_id: Optional[int] = None,
        conn: Any = None,
    ) -> List[Vehicle]:
        """Obtiene la lista de vehículos de una categoría que no tienen ningún traslape en el rango de fechas."""
        t_id = self.current_tenant_id
        query = """
            SELECT 
                v.id_vehiculo,
                v.tenant_id,
                v.id_modelo,
                v.id_categoria,
                v.placa,
                v.vin,
                v.color,
                v.kilometraje_actual,
                v.nivel_combustible_actual,
                v.estado,
                v.km_proximo_mantenimiento,
                v.activo,
                m.nombre AS modelo_nombre,
                m.anio AS anio,
                mar.nombre AS marca_nombre,
                c.nombre AS categoria_nombre,
                c.tarifa_base_diaria AS tarifa_base_diaria
            FROM vehiculos v
            INNER JOIN modelos m ON v.id_modelo = m.id_modelo
            INNER JOIN marcas mar ON m.id_marca = mar.id_marca
            INNER JOIN categorias_vehiculo c ON v.id_categoria = c.id_categoria
            WHERE v.tenant_id = %s
              AND v.id_categoria = %s
              AND v.activo = TRUE
              AND v.estado != 'DE_BAJA'
              AND v.estado != 'EN_MANTENIMIENTO'
              AND v.id_vehiculo NOT IN (
                  -- Vehículos con reservas solapadas
                  SELECT r.id_vehiculo 
                  FROM reservas r 
                  WHERE r.tenant_id = %s
                    AND r.id_vehiculo IS NOT NULL 
                    AND r.estado IN ('CONFIRMADA', 'PENDIENTE')
                    AND (%s IS NULL OR r.id_reserva != %s)
                    AND tstzrange(r.fecha_hora_inicio, r.fecha_hora_fin, '[)') && tstzrange(%s, %s, '[)')
                  
                  UNION
                  
                  -- Vehículos con contratos solapados
                  SELECT ct.id_vehiculo 
                  FROM contratos ct 
                  WHERE ct.tenant_id = %s
                    AND ct.estado IN ('ACTIVO', 'EN_INSPECCION', 'EN_LIQUIDACION')
                    AND tstzrange(ct.fecha_hora_inicio_pactada, ct.fecha_hora_fin_pactada, '[)') && tstzrange(%s, %s, '[)')
              )
            ORDER BY v.placa ASC;
        """
        params = (
            t_id,
            id_categoria,
            t_id,
            exclude_reservation_id,
            exclude_reservation_id,
            start_dt,
            end_dt,
            t_id,
            start_dt,
            end_dt,
        )
        rows = self.execute_query(query, params, conn=conn)
        return [
            Vehicle(
                id_vehiculo=r["id_vehiculo"],
                tenant_id=r.get("tenant_id", 1),
                id_modelo=r["id_modelo"],
                id_categoria=r["id_categoria"],
                placa=r["placa"],
                vin=r["vin"],
                color=r["color"],
                kilometraje_actual=r["kilometraje_actual"],
                nivel_combustible_actual=Decimal(str(r["nivel_combustible_actual"])),
                estado=VehicleStatus(r["estado"]),
                km_proximo_mantenimiento=r["km_proximo_mantenimiento"],
                activo=r["activo"],
                modelo_nombre=r.get("modelo_nombre"),
                categoria_nombre=r.get("categoria_nombre"),
                marca_nombre=r.get("marca_nombre"),
                anio=r.get("anio"),
                tarifa_base_diaria=Decimal(str(r["tarifa_base_diaria"])) if r.get("tarifa_base_diaria") is not None else None,
            )
            for r in rows
        ]

    def count_reservations(self, conn: Any = None) -> int:
        """Retorna el total histórico de reservas de la agencia activa para generar correlativos."""
        query = "SELECT COUNT(*) FROM reservas WHERE tenant_id = %s;"
        return int(self.execute_scalar(query, (self.current_tenant_id,), conn=conn) or 0)
