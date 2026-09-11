"""Repositorio de acceso a datos para Pagos, Depósitos y Cobros (DAL)."""

from decimal import Decimal
from typing import Any, List, Optional

from src.core.logger import get_logger
from src.domain.enums import PaymentMethod, PaymentType
from src.domain.models import Payment
from src.repositories.base_repository import BaseRepository

logger = get_logger(__name__)


class PaymentRepository(BaseRepository[Payment]):
    """Operaciones de persistencia para el registro y auditoría de transacciones financieras."""

    @staticmethod
    def _map_row_to_payment(row: dict) -> Payment:
        """Mapea una fila de base de datos a un objeto Payment."""
        return Payment(
            id_pago=row["id_pago"],
            codigo_transaccion=row["codigo_transaccion"],
            id_contrato=row.get("id_contrato"),
            id_reserva=row.get("id_reserva"),
            id_liquidacion=row.get("id_liquidacion"),
            tipo_movimiento=PaymentType(row["tipo_movimiento"]),
            metodo_pago=PaymentMethod(row["metodo_pago"]),
            monto=Decimal(str(row["monto"])),
            fecha_hora=row.get("fecha_hora"),
            referencia=row.get("referencia"),
            id_usuario=row["id_usuario"],
            usuario_nombre=row.get("usuario_nombre"),
        )

    def create(self, payment: Payment, conn: Any = None) -> Payment:
        """Inserta un nuevo pago / movimiento financiero y retorna la entidad actualizada."""
        query = """
            INSERT INTO pagos (
                codigo_transaccion,
                id_contrato,
                id_reserva,
                id_liquidacion,
                tipo_movimiento,
                metodo_pago,
                monto,
                referencia,
                id_usuario
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_pago, fecha_hora;
        """
        params = (
            payment.codigo_transaccion,
            payment.id_contrato,
            payment.id_reserva,
            payment.id_liquidacion,
            payment.tipo_movimiento.value if isinstance(payment.tipo_movimiento, PaymentType) else str(payment.tipo_movimiento),
            payment.metodo_pago.value if isinstance(payment.metodo_pago, PaymentMethod) else str(payment.metodo_pago),
            payment.monto,
            payment.referencia,
            payment.id_usuario,
        )
        row = self.execute_query_one(query, params, conn=conn)
        if not row:
            raise RuntimeError("Error al registrar el pago: no se obtuvo fila generada.")

        payment.id_pago = row["id_pago"]
        payment.fecha_hora = row["fecha_hora"]
        logger.info(
            "Pago registrado exitosamente [%s] Tipo: %s, Monto: $%s",
            payment.codigo_transaccion,
            payment.tipo_movimiento.value,
            payment.monto,
        )
        return payment

    def list_by_contract(self, id_contrato: int, conn: Any = None) -> List[Payment]:
        """Obtiene todas las transacciones financieras asociadas a un contrato específico."""
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
        return [self._map_row_to_payment(r) for r in rows]

    def list_by_reservation(self, id_reserva: int, conn: Any = None) -> List[Payment]:
        """Obtiene las transacciones asociadas a una reserva (ej. anticipo)."""
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
            WHERE p.id_reserva = %s
            ORDER BY p.fecha_hora ASC;
        """
        rows = self.execute_query(query, (id_reserva,), conn=conn)
        return [self._map_row_to_payment(r) for r in rows]

    def count_payments(self, conn: Any = None) -> int:
        """Retorna el número total de pagos para generación de correlativos."""
        query = "SELECT COUNT(*) AS total FROM pagos;"
        row = self.execute_query_one(query, conn=conn)
        return row["total"] if row else 0
