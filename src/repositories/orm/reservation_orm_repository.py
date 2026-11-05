"""Repositorio ORM de acceso a datos para la entidad Reserva y Disponibilidad Temporal (SQLAlchemy 2.0)."""

from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from sqlalchemy import func, or_, select

from src.core.logger import get_logger
from src.database.orm_models import (
    ClienteORM,
    ContratoORM,
    ReservaORM,
    VehiculoORM,
)
from src.domain.enums import ReservationStatus
from src.domain.models import Reservation, Vehicle
from src.repositories.orm.base_orm_repository import BaseORMRepository

logger = get_logger(__name__)


class ReservationORMRepository(BaseORMRepository[Reservation]):
    """Operaciones de persistencia mediante SQLAlchemy 2.0 ORM para reservas y disponibilidad de flota."""

    def get_by_id(self, id_reserva: int, conn: Any = None) -> Optional[Reservation]:
        """Obtiene una reserva por su ID primario con detalles de cliente, categoría y vehículo.

        Args:
            id_reserva (int): Identificador primario de la reserva.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            Optional[Reservation]: Entidad de dominio Reservation o ``None`` si no existe.
        """
        with self.session_scope(conn) as s:
            stmt = select(ReservaORM).where(
                ReservaORM.id_reserva == id_reserva,
                ReservaORM.tenant_id == self.current_tenant_id,
            )
            orm_obj = s.execute(stmt).scalars().first()
            return orm_obj.to_domain() if orm_obj else None

    def get_by_codigo(self, codigo: str, conn: Any = None) -> Optional[Reservation]:
        """Obtiene una reserva por su código alfanumérico único dentro de la agencia activa.

        Args:
            codigo (str): Código alfanumérico de la reserva (ej. ``RES-202609-0001``).
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            Optional[Reservation]: Entidad de dominio Reservation o ``None`` si no existe.
        """
        clean_code = codigo.strip().upper()
        with self.session_scope(conn) as s:
            stmt = select(ReservaORM).where(
                func.upper(ReservaORM.codigo_reserva) == clean_code,
                ReservaORM.tenant_id == self.current_tenant_id,
            )
            orm_obj = s.execute(stmt).scalars().first()
            return orm_obj.to_domain() if orm_obj else None

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
        """Lista reservas de la agencia activa con soporte para filtros múltiples.

        Args:
            search (Optional[str]): Término de búsqueda por código, cliente o placa.
            status (Optional[str]): Estado de reserva para filtrar (o ``TODAS``).
            client_id (Optional[int]): Filtro por identificador de cliente.
            category_id (Optional[int]): Filtro por identificador de categoría vehicular.
            from_date (Optional[datetime]): Fecha/hora inicial mínima de la reserva.
            to_date (Optional[datetime]): Fecha/hora final máxima de la reserva.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            List[Reservation]: Lista de reservas ordenadas por fecha de inicio descendente.
        """
        with self.session_scope(conn) as s:
            stmt = (
                select(ReservaORM)
                .join(ClienteORM, ReservaORM.id_cliente == ClienteORM.id_cliente)
                .outerjoin(VehiculoORM, ReservaORM.id_vehiculo == VehiculoORM.id_vehiculo)
                .where(ReservaORM.tenant_id == self.current_tenant_id)
            )

            if search and search.strip():
                term = f"%{search.strip()}%"
                stmt = stmt.where(
                    or_(
                        ReservaORM.codigo_reserva.ilike(term),
                        ClienteORM.nombres.ilike(term),
                        ClienteORM.apellidos.ilike(term),
                        ClienteORM.identificacion.ilike(term),
                        VehiculoORM.placa.ilike(term),
                    )
                )

            if status and status.strip() and status != "TODAS":
                stmt = stmt.where(ReservaORM.estado == status.strip())

            if client_id is not None:
                stmt = stmt.where(ReservaORM.id_cliente == client_id)

            if category_id is not None:
                stmt = stmt.where(ReservaORM.id_categoria == category_id)

            if from_date is not None:
                stmt = stmt.where(ReservaORM.fecha_hora_inicio >= from_date)

            if to_date is not None:
                stmt = stmt.where(ReservaORM.fecha_hora_fin <= to_date)

            stmt = stmt.order_by(ReservaORM.fecha_hora_inicio.desc())
            rows = s.execute(stmt).scalars().unique().all()
            return [r.to_domain() for r in rows]

    def create(self, reservation: Reservation, conn: Any = None) -> Reservation:
        """Inserta una nueva reserva en PostgreSQL mediante ORM y retorna la entidad con su ID generado.

        Args:
            reservation (Reservation): Objeto de dominio con los datos de la reserva a crear.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            Reservation: Entidad de dominio actualizada con ``id_reserva``, ``tenant_id`` y ``fecha_creacion``.
        """
        target_tenant = self.current_tenant_id
        with self.session_scope(conn) as s:
            orm_obj = ReservaORM(
                tenant_id=target_tenant,
                codigo_reserva=reservation.codigo_reserva,
                id_cliente=reservation.id_cliente,
                id_categoria=reservation.id_categoria,
                id_vehiculo=reservation.id_vehiculo,
                fecha_hora_inicio=reservation.fecha_hora_inicio,
                fecha_hora_fin=reservation.fecha_hora_fin,
                monto_anticipo=Decimal(str(reservation.monto_anticipo)),
                estado=(
                    reservation.estado.value
                    if isinstance(reservation.estado, ReservationStatus)
                    else str(reservation.estado)
                ),
                id_usuario=reservation.id_usuario,
            )
            s.add(orm_obj)
            s.flush()
            s.refresh(orm_obj)

            reservation.id_reserva = orm_obj.id_reserva
            reservation.tenant_id = orm_obj.tenant_id
            reservation.fecha_creacion = orm_obj.fecha_creacion
            return reservation

    def update(self, reservation: Reservation, conn: Any = None) -> Reservation:
        """Actualiza los datos modificables de una reserva existente en la agencia activa.

        Args:
            reservation (Reservation): Entidad de dominio con los datos modificados.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            Reservation: La misma instancia de dominio actualizada.
        """
        with self.session_scope(conn) as s:
            stmt = select(ReservaORM).where(
                ReservaORM.id_reserva == reservation.id_reserva,
                ReservaORM.tenant_id == self.current_tenant_id,
            )
            orm_obj = s.execute(stmt).scalars().first()
            if orm_obj:
                orm_obj.id_cliente = reservation.id_cliente
                orm_obj.id_categoria = reservation.id_categoria
                orm_obj.id_vehiculo = reservation.id_vehiculo
                orm_obj.fecha_hora_inicio = reservation.fecha_hora_inicio
                orm_obj.fecha_hora_fin = reservation.fecha_hora_fin
                orm_obj.monto_anticipo = Decimal(str(reservation.monto_anticipo))
                orm_obj.estado = (
                    reservation.estado.value
                    if isinstance(reservation.estado, ReservationStatus)
                    else str(reservation.estado)
                )
                s.flush()
            return reservation

    def update_status(
        self, id_reserva: int, new_status: ReservationStatus, conn: Any = None
    ) -> None:
        """Actualiza únicamente el estado de una reserva.

        Args:
            id_reserva (int): Identificador primario de la reserva.
            new_status (ReservationStatus): Nuevo estado a asignar.
            conn (Any, optional): Sesión ORM compartida opcional.
        """
        with self.session_scope(conn) as s:
            stmt = select(ReservaORM).where(
                ReservaORM.id_reserva == id_reserva,
                ReservaORM.tenant_id == self.current_tenant_id,
            )
            orm_obj = s.execute(stmt).scalars().first()
            if orm_obj:
                orm_obj.estado = (
                    new_status.value
                    if isinstance(new_status, ReservationStatus)
                    else str(new_status)
                )
                s.flush()

    def check_vehicle_conflict(
        self,
        id_vehiculo: int,
        start_dt: datetime,
        end_dt: datetime,
        exclude_reservation_id: Optional[int] = None,
        conn: Any = None,
    ) -> bool:
        """Verifica si un vehículo específico presenta colisión de horario con reservas o contratos vigentes.

        Args:
            id_vehiculo (int): Identificador del vehículo a verificar.
            start_dt (datetime): Fecha y hora de inicio del intervalo solicitado.
            end_dt (datetime): Fecha y hora de fin del intervalo solicitado.
            exclude_reservation_id (Optional[int]): ID de reserva a excluir (en caso de edición).
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            bool: ``True`` si existe traslape temporal, ``False`` si está libre.
        """
        t_id = self.current_tenant_id
        with self.session_scope(conn) as s:
            res_stmt = select(ReservaORM.id_vehiculo).where(
                ReservaORM.id_vehiculo == id_vehiculo,
                ReservaORM.tenant_id == t_id,
                ReservaORM.estado.in_(["CONFIRMADA", "PENDIENTE"]),
                ReservaORM.fecha_hora_inicio < end_dt,
                ReservaORM.fecha_hora_fin > start_dt,
            )
            if exclude_reservation_id is not None:
                res_stmt = res_stmt.where(ReservaORM.id_reserva != exclude_reservation_id)

            if s.execute(res_stmt.limit(1)).first() is not None:
                return True

            ctr_stmt = select(ContratoORM.id_vehiculo).where(
                ContratoORM.id_vehiculo == id_vehiculo,
                ContratoORM.tenant_id == t_id,
                ContratoORM.estado.in_(["ACTIVO", "EN_INSPECCION", "EN_LIQUIDACION"]),
                ContratoORM.fecha_hora_inicio_pactada < end_dt,
                ContratoORM.fecha_hora_fin_pactada > start_dt,
            )
            return s.execute(ctr_stmt.limit(1)).first() is not None

    def get_available_vehicles_for_period(
        self,
        id_categoria: int,
        start_dt: datetime,
        end_dt: datetime,
        exclude_reservation_id: Optional[int] = None,
        conn: Any = None,
    ) -> List[Vehicle]:
        """Obtiene la lista de vehículos de una categoría sin ningún traslape en el rango de fechas.

        Args:
            id_categoria (int): Identificador de la categoría tarifaria solicitada.
            start_dt (datetime): Inicio del período requerido.
            end_dt (datetime): Fin del período requerido.
            exclude_reservation_id (Optional[int]): Reserva a excluir del chequeo de traslape.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            List[Vehicle]: Lista de vehículos disponibles ordenados por placa ascendente.
        """
        t_id = self.current_tenant_id
        with self.session_scope(conn) as s:
            conflicting_res = select(ReservaORM.id_vehiculo).where(
                ReservaORM.tenant_id == t_id,
                ReservaORM.id_vehiculo.is_not(None),
                ReservaORM.estado.in_(["CONFIRMADA", "PENDIENTE"]),
                ReservaORM.fecha_hora_inicio < end_dt,
                ReservaORM.fecha_hora_fin > start_dt,
            )
            if exclude_reservation_id is not None:
                conflicting_res = conflicting_res.where(
                    ReservaORM.id_reserva != exclude_reservation_id
                )

            conflicting_ctr = select(ContratoORM.id_vehiculo).where(
                ContratoORM.tenant_id == t_id,
                ContratoORM.estado.in_(["ACTIVO", "EN_INSPECCION", "EN_LIQUIDACION"]),
                ContratoORM.fecha_hora_inicio_pactada < end_dt,
                ContratoORM.fecha_hora_fin_pactada > start_dt,
            )

            stmt = (
                select(VehiculoORM)
                .where(
                    VehiculoORM.tenant_id == t_id,
                    VehiculoORM.id_categoria == id_categoria,
                    VehiculoORM.activo.is_(True),
                    VehiculoORM.estado != "DE_BAJA",
                    VehiculoORM.estado != "EN_MANTENIMIENTO",
                    VehiculoORM.id_vehiculo.not_in(conflicting_res),
                    VehiculoORM.id_vehiculo.not_in(conflicting_ctr),
                )
                .order_by(VehiculoORM.placa.asc())
            )
            rows = s.execute(stmt).scalars().unique().all()
            return [v.to_domain() for v in rows]

    def count_reservations(self, conn: Any = None) -> int:
        """Retorna el total histórico de reservas de la agencia activa para generar correlativos.

        Args:
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            int: Número total de reservas registradas en la sucursal activa.
        """
        with self.session_scope(conn) as s:
            stmt = select(func.count()).select_from(ReservaORM).where(
                ReservaORM.tenant_id == self.current_tenant_id
            )
            val = s.execute(stmt).scalar()
            return int(val or 0)
