"""Repositorio de acceso a datos para Liquidaciones Financieras y Cierre de Contratos (DAL)."""

from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from src.core.logger import get_logger
from src.domain.enums import PaymentMethod, PaymentType, SettlementStatus
from src.domain.models import Payment, Settlement
from src.repositories.base_repository import BaseRepository

logger = get_logger(__name__)


class SettlementRepository(BaseRepository[Settlement]):
    """Operaciones de persistencia para el cálculo y asentamiento de liquidaciones y balances contables."""

    @staticmethod
    def _map_row_to_settlement(row: dict) -> Settlement:
        """Mapea una fila relacional con JOINs a un objeto de dominio Settlement."""
        return Settlement(
            id_liquidacion=row["id_liquidacion"],
            id_contrato=row["id_contrato"],
            id_devolucion=row["id_devolucion"],
            fecha_liquidacion=row["fecha_liquidacion"],
            dias_facturados=row["dias_facturados"],
            subtotal_renta=Decimal(str(row["subtotal_renta"])),
            cargos_retraso=Decimal(str(row["cargos_retraso"])),
            cargos_combustible=Decimal(str(row["cargos_combustible"])),
            cargos_km_excedente=Decimal(str(row["cargos_km_excedente"])),
            cargos_danios=Decimal(str(row["cargos_danios"])),
            total_bruto=Decimal(str(row["total_bruto"])),
            monto_garantia_aplicado=Decimal(str(row["monto_garantia_aplicado"])),
            saldo_cliente=Decimal(str(row["saldo_cliente"])),
            estado_liquidacion=SettlementStatus(row["estado_liquidacion"]),
            id_usuario=row["id_usuario"],
            contrato_codigo=row.get("contrato_codigo"),
            cliente_nombre=row.get("cliente_nombre"),
            vehiculo_placa=row.get("vehiculo_placa"),
            usuario_nombre=row.get("usuario_nombre"),
            monto_garantia_inicial=Decimal(str(row.get("monto_garantia_inicial", "0.00"))),
        )

    def _load_settlement_payments(self, id_liquidacion: int, conn: Any = None) -> List[Payment]:
        """Recupera los pagos o reembolsos generados en la liquidación."""
        query = """
            SELECT id_pago, codigo_transaccion, id_contrato, id_reserva, id_liquidacion,
                   tipo_movimiento, metodo_pago, monto, fecha_hora, referencia, id_usuario
            FROM pagos
            WHERE id_liquidacion = %s
            ORDER BY id_pago ASC;
        """
        rows = self.execute_query(query, (id_liquidacion,), conn=conn)
        payments = []
        for r in rows:
            payments.append(
                Payment(
                    id_pago=r["id_pago"],
                    codigo_transaccion=r["codigo_transaccion"],
                    id_contrato=r.get("id_contrato"),
                    id_reserva=r.get("id_reserva"),
                    id_liquidacion=r.get("id_liquidacion"),
                    tipo_movimiento=PaymentType(r["tipo_movimiento"]),
                    metodo_pago=PaymentMethod(r["metodo_pago"]),
                    monto=Decimal(str(r["monto"])),
                    fecha_hora=r["fecha_hora"],
                    referencia=r.get("referencia"),
                    id_usuario=r["id_usuario"],
                )
            )
        return payments

    def create(self, settlement: Settlement, conn: Any = None) -> Settlement:
        """Inserta un registro de liquidación financiera en la base de datos."""
        query = """
            INSERT INTO liquidaciones (
                id_contrato,
                id_devolucion,
                fecha_liquidacion,
                dias_facturados,
                subtotal_renta,
                cargos_retraso,
                cargos_combustible,
                cargos_km_excedente,
                cargos_danios,
                total_bruto,
                monto_garantia_aplicado,
                saldo_cliente,
                estado_liquidacion,
                id_usuario
            ) VALUES (
                %(id_contrato)s,
                %(id_devolucion)s,
                %(fecha_liquidacion)s,
                %(dias_facturados)s,
                %(subtotal_renta)s,
                %(cargos_retraso)s,
                %(cargos_combustible)s,
                %(cargos_km_excedente)s,
                %(cargos_danios)s,
                %(total_bruto)s,
                %(monto_garantia_aplicado)s,
                %(saldo_cliente)s,
                %(estado_liquidacion)s,
                %(id_usuario)s
            ) RETURNING id_liquidacion;
        """
        params = {
            "id_contrato": settlement.id_contrato,
            "id_devolucion": settlement.id_devolucion,
            "fecha_liquidacion": settlement.fecha_liquidacion or datetime.now(),
            "dias_facturados": settlement.dias_facturados,
            "subtotal_renta": settlement.subtotal_renta,
            "cargos_retraso": settlement.cargos_retraso,
            "cargos_combustible": settlement.cargos_combustible,
            "cargos_km_excedente": settlement.cargos_km_excedente,
            "cargos_danios": settlement.cargos_danios,
            "total_bruto": settlement.total_bruto,
            "monto_garantia_aplicado": settlement.monto_garantia_aplicado,
            "saldo_cliente": settlement.saldo_cliente,
            "estado_liquidacion": settlement.estado_liquidacion.value if hasattr(settlement.estado_liquidacion, "value") else str(settlement.estado_liquidacion),
            "id_usuario": settlement.id_usuario,
        }

        created_id = self.execute_scalar(query, params, conn=conn)
        settlement.id_liquidacion = created_id
        logger.info(
            "Liquidación ID %s registrada para contrato ID %s (Total Bruto: $%s, Saldo: $%s).",
            created_id,
            settlement.id_contrato,
            settlement.total_bruto,
            settlement.saldo_cliente,
        )
        return settlement

    def get_by_id(self, id_liquidacion: int, conn: Any = None) -> Optional[Settlement]:
        """Recupera una liquidación por su identificador primario."""
        query = """
            SELECT 
                l.id_liquidacion,
                l.id_contrato,
                l.id_devolucion,
                l.fecha_liquidacion,
                l.dias_facturados,
                l.subtotal_renta,
                l.cargos_retraso,
                l.cargos_combustible,
                l.cargos_km_excedente,
                l.cargos_danios,
                l.total_bruto,
                l.monto_garantia_aplicado,
                l.saldo_cliente,
                l.estado_liquidacion,
                l.id_usuario,
                c.codigo_contrato AS contrato_codigo,
                c.monto_garantia AS monto_garantia_inicial,
                CONCAT(cl.nombres, ' ', cl.apellidos) AS cliente_nombre,
                v.placa AS vehiculo_placa,
                u.nombre_completo AS usuario_nombre
            FROM liquidaciones l
            INNER JOIN contratos c ON l.id_contrato = c.id_contrato
            INNER JOIN clientes cl ON c.id_cliente = cl.id_cliente
            INNER JOIN vehiculos v ON c.id_vehiculo = v.id_vehiculo
            INNER JOIN usuarios u ON l.id_usuario = u.id_usuario
            WHERE l.id_liquidacion = %s;
        """
        row = self.execute_query_one(query, (id_liquidacion,), conn=conn)
        if not row:
            return None
        settlement = self._map_row_to_settlement(row)
        settlement.pagos = self._load_settlement_payments(settlement.id_liquidacion, conn=conn)
        return settlement

    def get_by_contract_id(self, id_contrato: int, conn: Any = None) -> Optional[Settlement]:
        """Obtiene la liquidación asociada a un contrato específico."""
        query = """
            SELECT 
                l.id_liquidacion,
                l.id_contrato,
                l.id_devolucion,
                l.fecha_liquidacion,
                l.dias_facturados,
                l.subtotal_renta,
                l.cargos_retraso,
                l.cargos_combustible,
                l.cargos_km_excedente,
                l.cargos_danios,
                l.total_bruto,
                l.monto_garantia_aplicado,
                l.saldo_cliente,
                l.estado_liquidacion,
                l.id_usuario,
                c.codigo_contrato AS contrato_codigo,
                c.monto_garantia AS monto_garantia_inicial,
                CONCAT(cl.nombres, ' ', cl.apellidos) AS cliente_nombre,
                v.placa AS vehiculo_placa,
                u.nombre_completo AS usuario_nombre
            FROM liquidaciones l
            INNER JOIN contratos c ON l.id_contrato = c.id_contrato
            INNER JOIN clientes cl ON c.id_cliente = cl.id_cliente
            INNER JOIN vehiculos v ON c.id_vehiculo = v.id_vehiculo
            INNER JOIN usuarios u ON l.id_usuario = u.id_usuario
            WHERE l.id_contrato = %s;
        """
        row = self.execute_query_one(query, (id_contrato,), conn=conn)
        if not row:
            return None
        settlement = self._map_row_to_settlement(row)
        settlement.pagos = self._load_settlement_payments(settlement.id_liquidacion, conn=conn)
        return settlement

    def list_all(
        self,
        search: str = "",
        limit: int = 100,
        conn: Any = None,
    ) -> List[Settlement]:
        """Lista las liquidaciones registradas en el sistema."""
        base_query = """
            SELECT 
                l.id_liquidacion,
                l.id_contrato,
                l.id_devolucion,
                l.fecha_liquidacion,
                l.dias_facturados,
                l.subtotal_renta,
                l.cargos_retraso,
                l.cargos_combustible,
                l.cargos_km_excedente,
                l.cargos_danios,
                l.total_bruto,
                l.monto_garantia_aplicado,
                l.saldo_cliente,
                l.estado_liquidacion,
                l.id_usuario,
                c.codigo_contrato AS contrato_codigo,
                c.monto_garantia AS monto_garantia_inicial,
                CONCAT(cl.nombres, ' ', cl.apellidos) AS cliente_nombre,
                v.placa AS vehiculo_placa,
                u.nombre_completo AS usuario_nombre
            FROM liquidaciones l
            INNER JOIN contratos c ON l.id_contrato = c.id_contrato
            INNER JOIN clientes cl ON c.id_cliente = cl.id_cliente
            INNER JOIN vehiculos v ON c.id_vehiculo = v.id_vehiculo
            INNER JOIN usuarios u ON l.id_usuario = u.id_usuario
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
                )
            """
            params.extend([search_pattern] * 4)

        base_query += " ORDER BY l.fecha_liquidacion DESC LIMIT %s;"
        params.append(limit)

        rows = self.execute_query(base_query, tuple(params), conn=conn)
        return [self._map_row_to_settlement(r) for r in rows]

    def count_settlements(self, conn: Any = None) -> int:
        """Obtiene la cantidad total de liquidaciones registradas."""
        query = "SELECT COUNT(*) FROM liquidaciones;"
        return int(self.execute_scalar(query, conn=conn) or 0)
