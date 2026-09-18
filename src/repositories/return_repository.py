"""Repositorio de acceso a datos para Devoluciones de Vehículos e Inspecciones de Retorno (DAL)."""

from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from src.core.logger import get_logger
from src.domain.enums import DamageSeverity, DamageType
from src.domain.models import Damage, ReturnInspection
from src.repositories.base_repository import BaseRepository

logger = get_logger(__name__)


class ReturnRepository(BaseRepository[ReturnInspection]):
    """Operaciones de persistencia para la recepción física, odómetro, combustible y registro de averías."""

    @staticmethod
    def _map_row_to_damage(row: dict) -> Damage:
        """Mapea una fila relacional de la tabla danios a un objeto de dominio Damage."""
        return Damage(
            id_danio=row["id_danio"],
            id_devolucion=row["id_devolucion"],
            zona_carroceria=row["zona_carroceria"],
            tipo_danio=DamageType(row["tipo_danio"]),
            gravedad=DamageSeverity(row["gravedad"]),
            descripcion=row["descripcion"],
            costo_reparacion=Decimal(str(row["costo_reparacion"])),
        )

    @staticmethod
    def _map_row_to_return(row: dict) -> ReturnInspection:
        """Mapea una fila relacional con JOINs a un objeto ReturnInspection."""
        return ReturnInspection(
            id_devolucion=row["id_devolucion"],
            id_contrato=row["id_contrato"],
            fecha_hora_retorno_real=row["fecha_hora_retorno_real"],
            kilometraje_retorno=row["kilometraje_retorno"],
            combustible_retorno=Decimal(str(row["combustible_retorno"])),
            horas_retraso=row["horas_retraso"],
            limpieza_aprobada=row["limpieza_aprobada"],
            accesorios_completos=row["accesorios_completos"],
            observaciones=row.get("observaciones"),
            id_usuario=row["id_usuario"],
            contrato_codigo=row.get("contrato_codigo"),
            cliente_nombre=row.get("cliente_nombre"),
            cliente_identificacion=row.get("cliente_identificacion"),
            vehiculo_placa=row.get("vehiculo_placa"),
            vehiculo_modelo=row.get("vehiculo_modelo"),
            usuario_nombre=row.get("usuario_nombre"),
            kilometraje_salida=row.get("kilometraje_salida", 0),
            combustible_salida=Decimal(str(row.get("combustible_salida", "1.00"))),
            fecha_hora_fin_pactada=row.get("fecha_hora_fin_pactada"),
            tarifa_diaria=Decimal(str(row.get("tarifa_diaria_aplicada", "0.00"))),
        )

    def _load_damages(self, id_devolucion: int, conn: Any = None) -> List[Damage]:
        """Recupera la lista de averías registradas para una devolución específica."""
        query = """
            SELECT id_danio, id_devolucion, zona_carroceria, tipo_danio, gravedad, descripcion, costo_reparacion
            FROM danios
            WHERE id_devolucion = %s
            ORDER BY id_danio ASC;
        """
        rows = self.execute_query(query, (id_devolucion,), conn=conn)
        return [self._map_row_to_damage(r) for r in rows]

    def create(self, return_data: ReturnInspection, conn: Any = None) -> ReturnInspection:
        """Inserta la devolución física y sus daños asociados en la base de datos."""
        query_devolucion = """
            INSERT INTO devoluciones (
                id_contrato,
                fecha_hora_retorno_real,
                kilometraje_retorno,
                combustible_retorno,
                horas_retraso,
                limpieza_aprobada,
                accesorios_completos,
                observaciones,
                id_usuario
            ) VALUES (
                %(id_contrato)s,
                %(fecha_hora_retorno_real)s,
                %(kilometraje_retorno)s,
                %(combustible_retorno)s,
                %(horas_retraso)s,
                %(limpieza_aprobada)s,
                %(accesorios_completos)s,
                %(observaciones)s,
                %(id_usuario)s
            ) RETURNING id_devolucion;
        """
        params = {
            "id_contrato": return_data.id_contrato,
            "fecha_hora_retorno_real": return_data.fecha_hora_retorno_real or datetime.now(),
            "kilometraje_retorno": return_data.kilometraje_retorno,
            "combustible_retorno": return_data.combustible_retorno,
            "horas_retraso": return_data.horas_retraso,
            "limpieza_aprobada": return_data.limpieza_aprobada,
            "accesorios_completos": return_data.accesorios_completos,
            "observaciones": return_data.observaciones,
            "id_usuario": return_data.id_usuario,
        }

        created_id = self.execute_scalar(query_devolucion, params, conn=conn)
        return_data.id_devolucion = created_id

        # Insertar detalle de daños físicos detectados
        if return_data.danios:
            query_danio = """
                INSERT INTO danios (
                    id_devolucion,
                    zona_carroceria,
                    tipo_danio,
                    gravedad,
                    descripcion,
                    costo_reparacion
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id_danio;
            """
            for danio in return_data.danios:
                danio_params = (
                    created_id,
                    danio.zona_carroceria,
                    danio.tipo_danio.value if hasattr(danio.tipo_danio, "value") else str(danio.tipo_danio),
                    danio.gravedad.value if hasattr(danio.gravedad, "value") else str(danio.gravedad),
                    danio.descripcion,
                    danio.costo_reparacion,
                )
                danio.id_danio = self.execute_scalar(query_danio, danio_params, conn=conn)
                danio.id_devolucion = created_id

        logger.info(
            "Devolución ID %s registrada para contrato ID %s con %d daños asociados.",
            created_id,
            return_data.id_contrato,
            len(return_data.danios),
        )
        return return_data

    def get_by_id(self, id_devolucion: int, conn: Any = None) -> Optional[ReturnInspection]:
        """Recupera un acta de devolución por su identificador primario con sus averías asociadas."""
        query = """
            SELECT 
                d.id_devolucion,
                d.id_contrato,
                d.fecha_hora_retorno_real,
                d.kilometraje_retorno,
                d.combustible_retorno,
                d.horas_retraso,
                d.limpieza_aprobada,
                d.accesorios_completos,
                d.observaciones,
                d.id_usuario,
                c.codigo_contrato AS contrato_codigo,
                c.kilometraje_salida,
                c.combustible_salida,
                c.fecha_hora_fin_pactada,
                c.tarifa_diaria_aplicada,
                CONCAT(cl.nombres, ' ', cl.apellidos) AS cliente_nombre,
                cl.identificacion AS cliente_identificacion,
                v.placa AS vehiculo_placa,
                CONCAT(ma.nombre, ' ', mo.nombre) AS vehiculo_modelo,
                u.nombre_completo AS usuario_nombre
            FROM devoluciones d
            INNER JOIN contratos c ON d.id_contrato = c.id_contrato
            INNER JOIN clientes cl ON c.id_cliente = cl.id_cliente
            INNER JOIN vehiculos v ON c.id_vehiculo = v.id_vehiculo
            INNER JOIN modelos mo ON v.id_modelo = mo.id_modelo
            INNER JOIN marcas ma ON mo.id_marca = ma.id_marca
            INNER JOIN usuarios u ON d.id_usuario = u.id_usuario
            WHERE d.id_devolucion = %s;
        """
        row = self.execute_query_one(query, (id_devolucion,), conn=conn)
        if not row:
            return None

        ret = self._map_row_to_return(row)
        ret.danios = self._load_damages(ret.id_devolucion, conn=conn)
        return ret

    def get_by_contract_id(self, id_contrato: int, conn: Any = None) -> Optional[ReturnInspection]:
        """Obtiene la devolución asociada a un contrato si ya fue recibida."""
        query = """
            SELECT 
                d.id_devolucion,
                d.id_contrato,
                d.fecha_hora_retorno_real,
                d.kilometraje_retorno,
                d.combustible_retorno,
                d.horas_retraso,
                d.limpieza_aprobada,
                d.accesorios_completos,
                d.observaciones,
                d.id_usuario,
                c.codigo_contrato AS contrato_codigo,
                c.kilometraje_salida,
                c.combustible_salida,
                c.fecha_hora_fin_pactada,
                c.tarifa_diaria_aplicada,
                CONCAT(cl.nombres, ' ', cl.apellidos) AS cliente_nombre,
                cl.identificacion AS cliente_identificacion,
                v.placa AS vehiculo_placa,
                CONCAT(ma.nombre, ' ', mo.nombre) AS vehiculo_modelo,
                u.nombre_completo AS usuario_nombre
            FROM devoluciones d
            INNER JOIN contratos c ON d.id_contrato = c.id_contrato
            INNER JOIN clientes cl ON c.id_cliente = cl.id_cliente
            INNER JOIN vehiculos v ON c.id_vehiculo = v.id_vehiculo
            INNER JOIN modelos mo ON v.id_modelo = mo.id_modelo
            INNER JOIN marcas ma ON mo.id_marca = ma.id_marca
            INNER JOIN usuarios u ON d.id_usuario = u.id_usuario
            WHERE d.id_contrato = %s;
        """
        row = self.execute_query_one(query, (id_contrato,), conn=conn)
        if not row:
            return None

        ret = self._map_row_to_return(row)
        ret.danios = self._load_damages(ret.id_devolucion, conn=conn)
        return ret

    def list_all(
        self,
        search: str = "",
        limit: int = 100,
        conn: Any = None,
    ) -> List[ReturnInspection]:
        """Lista las actas de devolución registradas con filtros opcionales de búsqueda."""
        base_query = """
            SELECT 
                d.id_devolucion,
                d.id_contrato,
                d.fecha_hora_retorno_real,
                d.kilometraje_retorno,
                d.combustible_retorno,
                d.horas_retraso,
                d.limpieza_aprobada,
                d.accesorios_completos,
                d.observaciones,
                d.id_usuario,
                c.codigo_contrato AS contrato_codigo,
                c.kilometraje_salida,
                c.combustible_salida,
                c.fecha_hora_fin_pactada,
                c.tarifa_diaria_aplicada,
                CONCAT(cl.nombres, ' ', cl.apellidos) AS cliente_nombre,
                cl.identificacion AS cliente_identificacion,
                v.placa AS vehiculo_placa,
                CONCAT(ma.nombre, ' ', mo.nombre) AS vehiculo_modelo,
                u.nombre_completo AS usuario_nombre
            FROM devoluciones d
            INNER JOIN contratos c ON d.id_contrato = c.id_contrato
            INNER JOIN clientes cl ON c.id_cliente = cl.id_cliente
            INNER JOIN vehiculos v ON c.id_vehiculo = v.id_vehiculo
            INNER JOIN modelos mo ON v.id_modelo = mo.id_modelo
            INNER JOIN marcas ma ON mo.id_marca = ma.id_marca
            INNER JOIN usuarios u ON d.id_usuario = u.id_usuario
            WHERE 1=1
        """
        params: List[Any] = []
        if search:
            search_pattern = f"%{search.strip()}%"
            base_query += """
                AND (
                    c.codigo_contrato ILIKE %s
                    OR v.placa ILIKE %s
                    OR cl.nombres ILIKE %s
                    OR cl.apellidos ILIKE %s
                    OR cl.identificacion ILIKE %s
                )
            """
            params.extend([search_pattern] * 5)

        base_query += " ORDER BY d.fecha_hora_retorno_real DESC LIMIT %s;"
        params.append(limit)

        rows = self.execute_query(base_query, tuple(params), conn=conn)
        returns = [self._map_row_to_return(r) for r in rows]
        for r in returns:
            r.danios = self._load_damages(r.id_devolucion, conn=conn)
        return returns

    def count_returns(self, conn: Any = None) -> int:
        """Obtiene la cantidad total de devoluciones registradas."""
        query = "SELECT COUNT(*) FROM devoluciones;"
        return int(self.execute_scalar(query, conn=conn) or 0)
