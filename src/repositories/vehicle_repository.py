"""Repositorio de acceso a datos para la entidad Vehículo, Flota y Catálogos auxiliares (DAL)."""

from decimal import Decimal
from typing import Any, List, Optional
from src.core.logger import get_logger
from src.domain.enums import VehicleStatus
from src.domain.models import Brand, Vehicle, VehicleCategory, VehicleModel
from src.repositories.base_repository import BaseRepository

logger = get_logger(__name__)


class VehicleRepository(BaseRepository[Vehicle]):
    """Operaciones de persistencia para la gestión de flota, vehículos, marcas, modelos y categorías."""

    @staticmethod
    def _map_row_to_vehicle(row: dict) -> Vehicle:
        """Mapea una fila con JOINs de modelo, marca y categoría a un objeto Vehicle."""
        return Vehicle(
            id_vehiculo=row["id_vehiculo"],
            id_modelo=row["id_modelo"],
            id_categoria=row["id_categoria"],
            placa=row["placa"],
            vin=row["vin"],
            color=row["color"],
            kilometraje_actual=row["kilometraje_actual"],
            nivel_combustible_actual=Decimal(str(row["nivel_combustible_actual"])),
            estado=VehicleStatus(row["estado"]),
            km_proximo_mantenimiento=row["km_proximo_mantenimiento"],
            activo=row["activo"],
            modelo_nombre=row.get("modelo_nombre"),
            categoria_nombre=row.get("categoria_nombre"),
            marca_nombre=row.get("marca_nombre"),
            anio=row.get("anio"),
            tarifa_base_diaria=Decimal(str(row["tarifa_base_diaria"])) if row.get("tarifa_base_diaria") is not None else None,
        )

    def get_by_id(self, id_vehiculo: int, conn: Any = None) -> Optional[Vehicle]:
        """Obtiene un vehículo por su identificador primario con detalles de catálogo."""
        query = """
            SELECT 
                v.id_vehiculo,
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
            WHERE v.id_vehiculo = %s;
        """
        row = self.execute_query_one(query, (id_vehiculo,), conn=conn)
        return self._map_row_to_vehicle(row) if row else None

    def get_by_placa(self, placa: str, conn: Any = None) -> Optional[Vehicle]:
        """Obtiene un vehículo por su número de placa única."""
        query = """
            SELECT 
                v.id_vehiculo,
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
            WHERE UPPER(v.placa) = UPPER(%s);
        """
        row = self.execute_query_one(query, (placa.strip(),), conn=conn)
        return self._map_row_to_vehicle(row) if row else None

    def get_by_vin(self, vin: str, conn: Any = None) -> Optional[Vehicle]:
        """Obtiene un vehículo por su número VIN único."""
        query = """
            SELECT 
                v.id_vehiculo,
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
            WHERE UPPER(v.vin) = UPPER(%s);
        """
        row = self.execute_query_one(query, (vin.strip(),), conn=conn)
        return self._map_row_to_vehicle(row) if row else None

    def list_all(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        category_id: Optional[int] = None,
        active_only: bool = False,
        conn: Any = None,
    ) -> List[Vehicle]:
        """Lista vehículos con filtros opcionales de búsqueda, estado, categoría y actividad."""
        conditions = []
        params: List[Any] = []

        if active_only:
            conditions.append("v.activo = TRUE")

        if status and status.upper() != "TODOS":
            conditions.append("v.estado = %s")
            params.append(status.upper())

        if category_id is not None and category_id > 0:
            conditions.append("v.id_categoria = %s")
            params.append(category_id)

        if search and search.strip():
            term = f"%{search.strip()}%"
            conditions.append("""
                (v.placa ILIKE %s OR 
                 v.vin ILIKE %s OR 
                 v.color ILIKE %s OR 
                 m.nombre ILIKE %s OR 
                 mar.nombre ILIKE %s OR
                 c.nombre ILIKE %s)
            """)
            params.extend([term, term, term, term, term, term])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT 
                v.id_vehiculo,
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
            {where_clause}
            ORDER BY v.id_vehiculo DESC;
        """
        rows = self.execute_query(query, tuple(params) if params else None, conn=conn)
        return [self._map_row_to_vehicle(r) for r in rows]

    def create(self, vehicle: Vehicle, conn: Any = None) -> Vehicle:
        """Registra un nuevo vehículo en la base de datos."""
        query = """
            INSERT INTO vehiculos (
                id_modelo,
                id_categoria,
                placa,
                vin,
                color,
                kilometraje_actual,
                nivel_combustible_actual,
                estado,
                km_proximo_mantenimiento,
                activo
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_vehiculo;
        """
        params = (
            vehicle.id_modelo,
            vehicle.id_categoria,
            vehicle.placa.strip().upper(),
            vehicle.vin.strip().upper(),
            vehicle.color.strip(),
            vehicle.kilometraje_actual,
            float(vehicle.nivel_combustible_actual),
            vehicle.estado.value if isinstance(vehicle.estado, VehicleStatus) else str(vehicle.estado),
            vehicle.km_proximo_mantenimiento,
            vehicle.activo,
        )
        row = self.execute_query_one(query, params, conn=conn)
        if not row:
            raise RuntimeError("No se pudo obtener el ID del vehículo registrado.")

        vehicle.id_vehiculo = row["id_vehiculo"]
        logger.info("Vehículo creado exitosamente ID %s: %s (VIN: %s)", vehicle.id_vehiculo, vehicle.placa, vehicle.vin)
        return vehicle

    def update(self, vehicle: Vehicle, conn: Any = None) -> Vehicle:
        """Actualiza los datos técnicos y operativos de un vehículo existente."""
        query = """
            UPDATE vehiculos SET
                id_modelo = %s,
                id_categoria = %s,
                placa = %s,
                vin = %s,
                color = %s,
                kilometraje_actual = %s,
                nivel_combustible_actual = %s,
                estado = %s,
                km_proximo_mantenimiento = %s,
                activo = %s
            WHERE id_vehiculo = %s;
        """
        params = (
            vehicle.id_modelo,
            vehicle.id_categoria,
            vehicle.placa.strip().upper(),
            vehicle.vin.strip().upper(),
            vehicle.color.strip(),
            vehicle.kilometraje_actual,
            float(vehicle.nivel_combustible_actual),
            vehicle.estado.value if isinstance(vehicle.estado, VehicleStatus) else str(vehicle.estado),
            vehicle.km_proximo_mantenimiento,
            vehicle.activo,
            vehicle.id_vehiculo,
        )
        self.execute_non_query(query, params, conn=conn)
        logger.info("Vehículo actualizado exitosamente ID %s: %s", vehicle.id_vehiculo, vehicle.placa)
        return vehicle

    def update_status(self, id_vehiculo: int, new_status: VehicleStatus, conn: Any = None) -> bool:
        """Modifica exclusivamente el estado operativo de un vehículo."""
        query = "UPDATE vehiculos SET estado = %s WHERE id_vehiculo = %s;"
        status_val = new_status.value if isinstance(new_status, VehicleStatus) else str(new_status)
        count = self.execute_non_query(query, (status_val, id_vehiculo), conn=conn)
        logger.info("Estado del vehículo ID %s actualizado a '%s'", id_vehiculo, status_val)
        return count > 0

    def soft_delete(self, id_vehiculo: int, conn: Any = None) -> bool:
        """Desactiva un vehículo y cambia su estado a DE_BAJA."""
        query = "UPDATE vehiculos SET activo = FALSE, estado = 'DE_BAJA' WHERE id_vehiculo = %s;"
        count = self.execute_non_query(query, (id_vehiculo,), conn=conn)
        return count > 0

    def delete(self, id_vehiculo: int, conn: Any = None) -> bool:
        """Elimina físicamente el vehículo de la base de datos si no tiene restricciones."""
        query = "DELETE FROM vehiculos WHERE id_vehiculo = %s;"
        count = self.execute_non_query(query, (id_vehiculo,), conn=conn)
        return count > 0

    def has_active_commitments(self, id_vehiculo: int, conn: Any = None) -> bool:
        """Verifica si el vehículo está asignado a contratos o reservas vigentes."""
        query = """
            SELECT 
                (SELECT COUNT(*) FROM contratos WHERE id_vehiculo = %s AND estado IN ('ACTIVO', 'EN_INSPECCION', 'EN_LIQUIDACION')) +
                (SELECT COUNT(*) FROM reservas WHERE id_vehiculo = %s AND estado IN ('PENDIENTE', 'CONFIRMADA'))
            AS total_activos;
        """
        count = self.execute_scalar(query, (id_vehiculo, id_vehiculo), conn=conn)
        return (count or 0) > 0

    def has_any_history(self, id_vehiculo: int, conn: Any = None) -> bool:
        """Verifica si el vehículo posee historial en contratos, reservas o mantenimientos."""
        query = """
            SELECT 
                (SELECT COUNT(*) FROM contratos WHERE id_vehiculo = %s) +
                (SELECT COUNT(*) FROM reservas WHERE id_vehiculo = %s) +
                (SELECT COUNT(*) FROM mantenimientos WHERE id_vehiculo = %s)
            AS total_historial;
        """
        count = self.execute_scalar(query, (id_vehiculo, id_vehiculo, id_vehiculo), conn=conn)
        return (count or 0) > 0

    # ------------------------------------------------------------------------
    # Consultas auxiliares de Catálogos (Marcas, Modelos, Categorías)
    # ------------------------------------------------------------------------

    def list_brands(self, conn: Any = None) -> List[Brand]:
        """Lista todas las marcas registradas ordenadas alfabéticamente."""
        query = "SELECT id_marca, nombre FROM marcas ORDER BY nombre ASC;"
        rows = self.execute_query(query, conn=conn)
        return [Brand(id_marca=r["id_marca"], nombre=r["nombre"]) for r in rows]

    def list_models(self, id_marca: Optional[int] = None, conn: Any = None) -> List[VehicleModel]:
        """Lista modelos de vehículos, opcionalmente filtrados por marca."""
        if id_marca:
            query = """
                SELECT m.id_modelo, m.id_marca, m.nombre, m.anio, m.tipo_transmision, m.capacidad_pasajeros, mar.nombre AS marca_nombre
                FROM modelos m
                INNER JOIN marcas mar ON m.id_marca = mar.id_marca
                WHERE m.id_marca = %s
                ORDER BY m.nombre ASC, m.anio DESC;
            """
            rows = self.execute_query(query, (id_marca,), conn=conn)
        else:
            query = """
                SELECT m.id_modelo, m.id_marca, m.nombre, m.anio, m.tipo_transmision, m.capacidad_pasajeros, mar.nombre AS marca_nombre
                FROM modelos m
                INNER JOIN marcas mar ON m.id_marca = mar.id_marca
                ORDER BY mar.nombre ASC, m.nombre ASC, m.anio DESC;
            """
            rows = self.execute_query(query, conn=conn)

        return [
            VehicleModel(
                id_modelo=r["id_modelo"],
                id_marca=r["id_marca"],
                nombre=r["nombre"],
                anio=r["anio"],
                tipo_transmision=r["tipo_transmision"],
                capacidad_pasajeros=r["capacidad_pasajeros"],
                marca_nombre=r.get("marca_nombre"),
            )
            for r in rows
        ]

    def list_categories(self, conn: Any = None) -> List[VehicleCategory]:
        """Lista todas las categorías de vehículos con tarifas base."""
        query = """
            SELECT id_categoria, nombre, descripcion, deposito_garantia_sugerido, tarifa_base_diaria
            FROM categorias_vehiculo
            ORDER BY tarifa_base_diaria ASC;
        """
        rows = self.execute_query(query, conn=conn)
        return [
            VehicleCategory(
                id_categoria=r["id_categoria"],
                nombre=r["nombre"],
                descripcion=r.get("descripcion"),
                deposito_garantia_sugerido=Decimal(str(r["deposito_garantia_sugerido"])),
                tarifa_base_diaria=Decimal(str(r["tarifa_base_diaria"])),
            )
            for r in rows
        ]
