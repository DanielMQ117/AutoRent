"""Repositorio de acceso a datos para Contratos de Alquiler, Entrega y Conductores (DAL)."""

from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from src.core.logger import get_logger
from src.domain.enums import ContractStatus, PaymentMethod, PaymentType
from src.domain.models import AdditionalDriver, Contract, Payment
from src.repositories.base_repository import BaseRepository

logger = get_logger(__name__)


class ContractRepository(BaseRepository[Contract]):
    """Operaciones de persistencia para la gestión integral de contratos, salidas e inspecciones iniciales."""

    @staticmethod
    def _map_row_to_contract(row: dict) -> Contract:
        """Mapea una fila relacional con JOINs a un objeto de dominio Contract."""
        return Contract(
            id_contrato=row["id_contrato"],
            codigo_contrato=row["codigo_contrato"],
            id_reserva=row.get("id_reserva"),
            id_cliente=row["id_cliente"],
            id_vehiculo=row["id_vehiculo"],
            id_cobertura=row["id_cobertura"],
            fecha_hora_inicio_pactada=row["fecha_hora_inicio_pactada"],
            fecha_hora_fin_pactada=row["fecha_hora_fin_pactada"],
            fecha_hora_salida_real=row.get("fecha_hora_salida_real"),
            kilometraje_salida=row["kilometraje_salida"],
            combustible_salida=Decimal(str(row["combustible_salida"])),
            tarifa_diaria_aplicada=Decimal(str(row["tarifa_diaria_aplicada"])),
            monto_garantia=Decimal(str(row["monto_garantia"])),
            kilometraje_ilimitado=row["kilometraje_ilimitado"],
            limite_km_diario=row.get("limite_km_diario"),
            costo_km_excedente=Decimal(str(row["costo_km_excedente"])),
            estado=ContractStatus(row["estado"]),
            id_usuario=row["id_usuario"],
            fecha_creacion=row.get("fecha_creacion"),
            cliente_nombre=row.get("cliente_nombre"),
            cliente_identificacion=row.get("cliente_identificacion"),
            cliente_telefono=row.get("cliente_telefono"),
            vehiculo_placa=row.get("vehiculo_placa"),
            vehiculo_modelo=row.get("vehiculo_modelo"),
            vehiculo_categoria=row.get("vehiculo_categoria"),
            cobertura_nombre=row.get("cobertura_nombre"),
            cobertura_costo_diario=Decimal(str(row["cobertura_costo_diario"])) if row.get("cobertura_costo_diario") is not None else None,
            usuario_nombre=row.get("usuario_nombre"),
            reserva_codigo=row.get("reserva_codigo"),
        )

    def _load_additional_drivers(self, id_contrato: int, conn: Any = None) -> List[AdditionalDriver]:
        """Recupera la lista de conductores adicionales registrados para un contrato."""
        query = """
            SELECT id_conductor, id_contrato, nombre_completo, identificacion, numero_licencia, fecha_vencimiento_licencia
            FROM conductores_adicionales
            WHERE id_contrato = %s
            ORDER BY id_conductor ASC;
        """
        rows = self.execute_query(query, (id_contrato,), conn=conn)
        return [
            AdditionalDriver(
                id_conductor=r["id_conductor"],
                id_contrato=r["id_contrato"],
                nombre_completo=r["nombre_completo"],
                identificacion=r["identificacion"],
                numero_licencia=r["numero_licencia"],
                fecha_vencimiento_licencia=r["fecha_vencimiento_licencia"],
            )
            for r in rows
        ]

    def _load_contract_payments(self, id_contrato: int, conn: Any = None) -> List[Payment]:
        """Recupera los pagos y depósitos de garantía asociados al contrato."""
        query = """
            SELECT 
                p.id_pago,
                p.codigo_transaccion,
                p.id_contrato,
                p.id_reserva,
                p.id_liquidacion,
                p.tipo_movimiento,
                p.metodo_pago,
                p.monto,
                p.fecha_hora,
                p.referencia,
                p.id_usuario,
                u.nombre_completo AS usuario_nombre
            FROM pagos p
            INNER JOIN usuarios u ON p.id_usuario = u.id_usuario
            WHERE p.id_contrato = %s
            ORDER BY p.fecha_hora ASC;
        """
        rows = self.execute_query(query, (id_contrato,), conn=conn)
        return [
            Payment(
                id_pago=r["id_pago"],
                codigo_transaccion=r["codigo_transaccion"],
                id_contrato=r["id_contrato"],
                id_reserva=r.get("id_reserva"),
                id_liquidacion=r.get("id_liquidacion"),
                tipo_movimiento=PaymentType(r["tipo_movimiento"]),
                metodo_pago=PaymentMethod(r["metodo_pago"]),
                monto=Decimal(str(r["monto"])),
                fecha_hora=r.get("fecha_hora"),
                referencia=r.get("referencia"),
                id_usuario=r["id_usuario"],
                usuario_nombre=r.get("usuario_nombre"),
            )
            for r in rows
        ]

    def get_by_id(self, id_contrato: int, conn: Any = None) -> Optional[Contract]:
        """Obtiene un contrato por su ID primario con todos sus datos relacionales, conductores y pagos."""
        query = """
            SELECT 
                c.id_contrato,
                c.codigo_contrato,
                c.id_reserva,
                c.id_cliente,
                c.id_vehiculo,
                c.id_cobertura,
                c.fecha_hora_inicio_pactada,
                c.fecha_hora_fin_pactada,
                c.fecha_hora_salida_real,
                c.kilometraje_salida,
                c.combustible_salida,
                c.tarifa_diaria_aplicada,
                c.monto_garantia,
                c.kilometraje_ilimitado,
                c.limite_km_diario,
                c.costo_km_excedente,
                c.estado,
                c.id_usuario,
                c.fecha_creacion,
                (cl.nombres || ' ' || cl.apellidos) AS cliente_nombre,
                cl.identificacion AS cliente_identificacion,
                cl.telefono AS cliente_telefono,
                v.placa AS vehiculo_placa,
                (mar.nombre || ' ' || m.nombre) AS vehiculo_modelo,
                cat.nombre AS vehiculo_categoria,
                cob.nombre AS cobertura_nombre,
                cob.costo_diario AS cobertura_costo_diario,
                u.nombre_completo AS usuario_nombre,
                r.codigo_reserva AS reserva_codigo
            FROM contratos c
            INNER JOIN clientes cl ON c.id_cliente = cl.id_cliente
            INNER JOIN vehiculos v ON c.id_vehiculo = v.id_vehiculo
            INNER JOIN modelos m ON v.id_modelo = m.id_modelo
            INNER JOIN marcas mar ON m.id_marca = mar.id_marca
            INNER JOIN categorias_vehiculo cat ON v.id_categoria = cat.id_categoria
            INNER JOIN coberturas_seguro cob ON c.id_cobertura = cob.id_cobertura
            INNER JOIN usuarios u ON c.id_usuario = u.id_usuario
            LEFT JOIN reservas r ON c.id_reserva = r.id_reserva
            WHERE c.id_contrato = %s;
        """
        row = self.execute_query_one(query, (id_contrato,), conn=conn)
        if not row:
            return None

        contract = self._map_row_to_contract(row)
        contract.conductores_adicionales = self._load_additional_drivers(id_contrato, conn=conn)
        contract.pagos = self._load_contract_payments(id_contrato, conn=conn)
        return contract

    def get_by_codigo(self, codigo_contrato: str, conn: Any = None) -> Optional[Contract]:
        """Obtiene un contrato por su código único alfanumérico (ej. CTR-202609-0001)."""
        query = """
            SELECT 
                c.id_contrato,
                c.codigo_contrato,
                c.id_reserva,
                c.id_cliente,
                c.id_vehiculo,
                c.id_cobertura,
                c.fecha_hora_inicio_pactada,
                c.fecha_hora_fin_pactada,
                c.fecha_hora_salida_real,
                c.kilometraje_salida,
                c.combustible_salida,
                c.tarifa_diaria_aplicada,
                c.monto_garantia,
                c.kilometraje_ilimitado,
                c.limite_km_diario,
                c.costo_km_excedente,
                c.estado,
                c.id_usuario,
                c.fecha_creacion,
                (cl.nombres || ' ' || cl.apellidos) AS cliente_nombre,
                cl.identificacion AS cliente_identificacion,
                cl.telefono AS cliente_telefono,
                v.placa AS vehiculo_placa,
                (mar.nombre || ' ' || m.nombre) AS vehiculo_modelo,
                cat.nombre AS vehiculo_categoria,
                cob.nombre AS cobertura_nombre,
                cob.costo_diario AS cobertura_costo_diario,
                u.nombre_completo AS usuario_nombre,
                r.codigo_reserva AS reserva_codigo
            FROM contratos c
            INNER JOIN clientes cl ON c.id_cliente = cl.id_cliente
            INNER JOIN vehiculos v ON c.id_vehiculo = v.id_vehiculo
            INNER JOIN modelos m ON v.id_modelo = m.id_modelo
            INNER JOIN marcas mar ON m.id_marca = mar.id_marca
            INNER JOIN categorias_vehiculo cat ON v.id_categoria = cat.id_categoria
            INNER JOIN coberturas_seguro cob ON c.id_cobertura = cob.id_cobertura
            INNER JOIN usuarios u ON c.id_usuario = u.id_usuario
            LEFT JOIN reservas r ON c.id_reserva = r.id_reserva
            WHERE UPPER(c.codigo_contrato) = UPPER(%s);
        """
        row = self.execute_query_one(query, (codigo_contrato.strip(),), conn=conn)
        if not row:
            return None

        contract = self._map_row_to_contract(row)
        contract.conductores_adicionales = self._load_additional_drivers(contract.id_contrato, conn=conn)
        contract.pagos = self._load_contract_payments(contract.id_contrato, conn=conn)
        return contract

    def get_by_reserva_id(self, id_reserva: int, conn: Any = None) -> Optional[Contract]:
        """Obtiene el contrato originado a partir de una reserva previa."""
        query = "SELECT id_contrato FROM contratos WHERE id_reserva = %s;"
        row = self.execute_query_one(query, (id_reserva,), conn=conn)
        if not row:
            return None
        return self.get_by_id(row["id_contrato"], conn=conn)

    def list_all(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        client_id: Optional[int] = None,
        vehicle_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        conn: Any = None,
    ) -> List[Contract]:
        """Lista contratos aplicando filtros opcionales de búsqueda, estado y período."""
        conditions = ["1=1"]
        params: list[Any] = []

        if search and search.strip():
            term = f"%{search.strip()}%"
            conditions.append("""
                (c.codigo_contrato ILIKE %s 
                 OR cl.nombres ILIKE %s 
                 OR cl.apellidos ILIKE %s 
                 OR cl.identificacion ILIKE %s 
                 OR v.placa ILIKE %s)
            """)
            params.extend([term, term, term, term, term])

        if status and status.strip() and status != "TODOS":
            conditions.append("c.estado = %s")
            params.append(status.strip())

        if client_id is not None:
            conditions.append("c.id_cliente = %s")
            params.append(client_id)

        if vehicle_id is not None:
            conditions.append("c.id_vehiculo = %s")
            params.append(vehicle_id)

        if from_date:
            conditions.append("c.fecha_hora_inicio_pactada >= %s")
            params.append(from_date)

        if to_date:
            conditions.append("c.fecha_hora_fin_pactada <= %s")
            params.append(to_date)

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT 
                c.id_contrato,
                c.codigo_contrato,
                c.id_reserva,
                c.id_cliente,
                c.id_vehiculo,
                c.id_cobertura,
                c.fecha_hora_inicio_pactada,
                c.fecha_hora_fin_pactada,
                c.fecha_hora_salida_real,
                c.kilometraje_salida,
                c.combustible_salida,
                c.tarifa_diaria_aplicada,
                c.monto_garantia,
                c.kilometraje_ilimitado,
                c.limite_km_diario,
                c.costo_km_excedente,
                c.estado,
                c.id_usuario,
                c.fecha_creacion,
                (cl.nombres || ' ' || cl.apellidos) AS cliente_nombre,
                cl.identificacion AS cliente_identificacion,
                cl.telefono AS cliente_telefono,
                v.placa AS vehiculo_placa,
                (mar.nombre || ' ' || m.nombre) AS vehiculo_modelo,
                cat.nombre AS vehiculo_categoria,
                cob.nombre AS cobertura_nombre,
                cob.costo_diario AS cobertura_costo_diario,
                u.nombre_completo AS usuario_nombre,
                r.codigo_reserva AS reserva_codigo
            FROM contratos c
            INNER JOIN clientes cl ON c.id_cliente = cl.id_cliente
            INNER JOIN vehiculos v ON c.id_vehiculo = v.id_vehiculo
            INNER JOIN modelos m ON v.id_modelo = m.id_modelo
            INNER JOIN marcas mar ON m.id_marca = mar.id_marca
            INNER JOIN categorias_vehiculo cat ON v.id_categoria = cat.id_categoria
            INNER JOIN coberturas_seguro cob ON c.id_cobertura = cob.id_cobertura
            INNER JOIN usuarios u ON c.id_usuario = u.id_usuario
            LEFT JOIN reservas r ON c.id_reserva = r.id_reserva
            WHERE {where_clause}
            ORDER BY c.fecha_hora_inicio_pactada DESC;
        """
        rows = self.execute_query(query, tuple(params), conn=conn)
        return [self._map_row_to_contract(r) for r in rows]

    def create(self, contract: Contract, conn: Any = None) -> Contract:
        """Inserta un nuevo contrato y sus conductores adicionales en PostgreSQL."""
        query_contract = """
            INSERT INTO contratos (
                codigo_contrato,
                id_reserva,
                id_cliente,
                id_vehiculo,
                id_cobertura,
                fecha_hora_inicio_pactada,
                fecha_hora_fin_pactada,
                fecha_hora_salida_real,
                kilometraje_salida,
                combustible_salida,
                tarifa_diaria_aplicada,
                monto_garantia,
                kilometraje_ilimitado,
                limite_km_diario,
                costo_km_excedente,
                estado,
                id_usuario
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_contrato, fecha_creacion;
        """
        params = (
            contract.codigo_contrato,
            contract.id_reserva,
            contract.id_cliente,
            contract.id_vehiculo,
            contract.id_cobertura,
            contract.fecha_hora_inicio_pactada,
            contract.fecha_hora_fin_pactada,
            contract.fecha_hora_salida_real or datetime.now(),
            contract.kilometraje_salida,
            contract.combustible_salida,
            contract.tarifa_diaria_aplicada,
            contract.monto_garantia,
            contract.kilometraje_ilimitado,
            contract.limite_km_diario,
            contract.costo_km_excedente,
            contract.estado.value if isinstance(contract.estado, ContractStatus) else str(contract.estado),
            contract.id_usuario,
        )
        row = self.execute_query_one(query_contract, params, conn=conn)
        if not row:
            raise RuntimeError("Error al persistir el contrato: no se obtuvo fila de retorno.")

        contract.id_contrato = row["id_contrato"]
        contract.fecha_creacion = row["fecha_creacion"]

        # Insertar conductores adicionales si fueron especificados
        if contract.conductores_adicionales:
            query_driver = """
                INSERT INTO conductores_adicionales (
                    id_contrato,
                    nombre_completo,
                    identificacion,
                    numero_licencia,
                    fecha_vencimiento_licencia
                ) VALUES (%s, %s, %s, %s, %s)
                RETURNING id_conductor;
            """
            for driver in contract.conductores_adicionales:
                driver.id_contrato = contract.id_contrato
                d_params = (
                    contract.id_contrato,
                    driver.nombre_completo.strip(),
                    driver.identificacion.strip(),
                    driver.numero_licencia.strip(),
                    driver.fecha_vencimiento_licencia,
                )
                d_row = self.execute_query_one(query_driver, d_params, conn=conn)
                if d_row:
                    driver.id_conductor = d_row["id_conductor"]

        logger.info("Contrato '%s' registrado exitosamente con ID %s", contract.codigo_contrato, contract.id_contrato)
        return contract

    def update_status(self, id_contrato: int, status: ContractStatus, conn: Any = None) -> bool:
        """Actualiza el estado operativo de un contrato."""
        query = "UPDATE contratos SET estado = %s WHERE id_contrato = %s;"
        val = status.value if isinstance(status, ContractStatus) else str(status)
        count = self.execute_non_query(query, (val, id_contrato), conn=conn)
        return count > 0

    def check_vehicle_contract_conflict(
        self,
        id_vehiculo: int,
        start_dt: datetime,
        end_dt: datetime,
        exclude_contract_id: Optional[int] = None,
        conn: Any = None,
    ) -> bool:
        """Comprueba si un vehículo ya se encuentra bajo un contrato activo en el rango indicado."""
        query = """
            SELECT 1 FROM contratos
            WHERE id_vehiculo = %s
              AND estado IN ('ACTIVO', 'EN_INSPECCION', 'EN_LIQUIDACION')
              AND tstzrange(fecha_hora_inicio_pactada, fecha_hora_fin_pactada, '[)') &&
                  tstzrange(%s::timestamptz, %s::timestamptz, '[)')
              AND (%s IS NULL OR id_contrato <> %s)
            LIMIT 1;
        """
        row = self.execute_query_one(
            query,
            (id_vehiculo, start_dt, end_dt, exclude_contract_id, exclude_contract_id),
            conn=conn,
        )
        return row is not None

    def get_active_contract_by_vehicle(self, id_vehiculo: int, conn: Any = None) -> Optional[Contract]:
        """Retorna el contrato activo actualmente en curso para un vehículo específico."""
        query = """
            SELECT id_contrato FROM contratos 
            WHERE id_vehiculo = %s AND estado = 'ACTIVO'
            LIMIT 1;
        """
        row = self.execute_query_one(query, (id_vehiculo,), conn=conn)
        if not row:
            return None
        return self.get_by_id(row["id_contrato"], conn=conn)

    def count_contracts(self, conn: Any = None) -> int:
        """Retorna el número total de contratos para generación del código correlativo."""
        query = "SELECT COUNT(*) AS total FROM contratos;"
        row = self.execute_query_one(query, conn=conn)
        return row["total"] if row else 0
