"""Repositorio SQLAlchemy 2.0 ORM para la entidad Vehículo, Flota y Catálogos Auxiliares."""

from decimal import Decimal
from typing import Any, List, Optional

from sqlalchemy import func, or_, select

from src.core.logger import get_logger
from src.database.orm_models import (
    CategoriaVehiculoORM,
    ContratoORM,
    MantenimientoORM,
    MarcaORM,
    ModeloORM,
    ReservaORM,
    VehiculoORM,
)
from src.domain.enums import VehicleStatus
from src.domain.models import Brand, Vehicle, VehicleCategory, VehicleModel
from src.repositories.orm.base_orm_repository import BaseORMRepository

logger = get_logger(__name__)


class VehicleORMRepository(BaseORMRepository[Vehicle]):
    """Operaciones de persistencia mediante SQLAlchemy 2.0 ORM para vehículos, marcas, modelos y categorías."""

    def get_by_id(self, id_vehiculo: int, conn: Any = None) -> Optional[Vehicle]:
        """Obtiene un vehículo por su identificador primario con detalles de modelo, marca y categoría.

        Args:
            id_vehiculo (int): Identificador primario del vehículo.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            Optional[Vehicle]: Entidad ``Vehicle`` enriquecida o ``None``.
        """
        t_id = self.current_tenant_id
        with self.session_scope(conn) as s:
            stmt = select(VehiculoORM).where(
                VehiculoORM.id_vehiculo == int(id_vehiculo),
                VehiculoORM.tenant_id == int(t_id),
            )
            obj = s.scalars(stmt).first()
            return obj.to_domain() if obj else None

    def get_by_placa(self, placa: str, conn: Any = None) -> Optional[Vehicle]:
        """Obtiene un vehículo por su número de placa única dentro de la agencia activa.

        Args:
            placa (str): Número de placa a buscar (insensible a mayúsculas/minúsculas).
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            Optional[Vehicle]: Entidad ``Vehicle`` si existe, o ``None``.
        """
        t_id = self.current_tenant_id
        clean_placa = placa.strip().upper()
        with self.session_scope(conn) as s:
            stmt = select(VehiculoORM).where(
                func.upper(VehiculoORM.placa) == clean_placa,
                VehiculoORM.tenant_id == int(t_id),
            )
            obj = s.scalars(stmt).first()
            return obj.to_domain() if obj else None

    def get_by_vin(self, vin: str, conn: Any = None) -> Optional[Vehicle]:
        """Obtiene un vehículo por su número de chasis (VIN) único dentro de la agencia activa.

        Args:
            vin (str): Código VIN de 17 caracteres a buscar.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            Optional[Vehicle]: Entidad ``Vehicle`` si existe, o ``None``.
        """
        t_id = self.current_tenant_id
        clean_vin = vin.strip().upper()
        with self.session_scope(conn) as s:
            stmt = select(VehiculoORM).where(
                func.upper(VehiculoORM.vin) == clean_vin,
                VehiculoORM.tenant_id == int(t_id),
            )
            obj = s.scalars(stmt).first()
            return obj.to_domain() if obj else None

    def list_all(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        category_id: Optional[int] = None,
        active_only: bool = False,
        include_inactive: Optional[bool] = None,
        conn: Any = None,
    ) -> List[Vehicle]:
        """Lista los vehículos de la agencia activa con filtros opcionales de búsqueda, estado y categoría.

        Args:
            search (Optional[str]): Búsqueda libre sobre placa, VIN, color, modelo, marca o categoría.
            status (Optional[str]): Filtro opcional por estado operativo (ej. ``DISPONIBLE``).
            category_id (Optional[int]): Filtro opcional por ID de categoría tarifaria.
            active_only (bool): Si es ``True``, filtra solo vehículos con ``activo = True``.
            include_inactive (Optional[bool]): Si se especifica como ``False``, filtra ``activo = True``.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            List[Vehicle]: Lista de vehículos ordenados de forma descendente por ``id_vehiculo``.
        """
        t_id = self.current_tenant_id
        with self.session_scope(conn) as s:
            stmt = (
                select(VehiculoORM)
                .join(ModeloORM, VehiculoORM.id_modelo == ModeloORM.id_modelo)
                .join(MarcaORM, ModeloORM.id_marca == MarcaORM.id_marca)
                .join(
                    CategoriaVehiculoORM,
                    VehiculoORM.id_categoria == CategoriaVehiculoORM.id_categoria,
                )
                .where(VehiculoORM.tenant_id == int(t_id))
            )

            if include_inactive is not None:
                if not include_inactive:
                    stmt = stmt.where(VehiculoORM.activo.is_(True))
            elif active_only:
                stmt = stmt.where(VehiculoORM.activo.is_(True))

            if status and status.upper() != "TODOS":
                stmt = stmt.where(VehiculoORM.estado == status.upper())

            if category_id is not None and int(category_id) > 0:
                stmt = stmt.where(VehiculoORM.id_categoria == int(category_id))

            if search and search.strip():
                term = f"%{search.strip()}%"
                stmt = stmt.where(
                    or_(
                        VehiculoORM.placa.ilike(term),
                        VehiculoORM.vin.ilike(term),
                        VehiculoORM.color.ilike(term),
                        ModeloORM.nombre.ilike(term),
                        MarcaORM.nombre.ilike(term),
                        CategoriaVehiculoORM.nombre.ilike(term),
                    )
                )

            stmt = stmt.order_by(VehiculoORM.id_vehiculo.desc())
            rows = s.scalars(stmt).unique().all()
            return [r.to_domain() for r in rows]

    def create(self, vehicle: Vehicle, conn: Any = None) -> Vehicle:
        """Registra un nuevo vehículo en la base de datos para la agencia activa.

        Args:
            vehicle (Vehicle): Entidad ``Vehicle`` con los datos técnicos a persistir.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            Vehicle: Entidad ``Vehicle`` creada con su ``id_vehiculo`` asignado.
        """
        target_tenant = self.current_tenant_id
        estado_str = (
            vehicle.estado.value
            if isinstance(vehicle.estado, VehicleStatus)
            else str(vehicle.estado)
        )

        with self.session_scope(conn) as s:
            orm_vehicle = VehiculoORM(
                tenant_id=int(target_tenant),
                id_modelo=int(vehicle.id_modelo),
                id_categoria=int(vehicle.id_categoria),
                placa=vehicle.placa.strip().upper(),
                vin=vehicle.vin.strip().upper(),
                color=vehicle.color.strip(),
                kilometraje_actual=int(vehicle.kilometraje_actual),
                nivel_combustible_actual=Decimal(str(vehicle.nivel_combustible_actual)),
                estado=estado_str,
                km_proximo_mantenimiento=int(vehicle.km_proximo_mantenimiento),
                activo=bool(vehicle.activo),
            )
            s.add(orm_vehicle)
            s.flush()
            s.refresh(orm_vehicle)
            created = orm_vehicle.to_domain()
            vehicle.id_vehiculo = created.id_vehiculo
            vehicle.tenant_id = created.tenant_id
            logger.info(
                "Vehículo creado exitosamente ID %s: %s (VIN: %s)",
                created.id_vehiculo,
                created.placa,
                created.vin,
            )
            return created

    def update(self, vehicle: Vehicle, conn: Any = None) -> Vehicle:
        """Actualiza los datos técnicos y operativos de un vehículo existente.

        Args:
            vehicle (Vehicle): Entidad ``Vehicle`` con los campos modificados.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            Vehicle: Entidad ``Vehicle`` actualizada.
        """
        t_id = self.current_tenant_id
        estado_str = (
            vehicle.estado.value
            if isinstance(vehicle.estado, VehicleStatus)
            else str(vehicle.estado)
        )

        with self.session_scope(conn) as s:
            stmt = select(VehiculoORM).where(
                VehiculoORM.id_vehiculo == int(vehicle.id_vehiculo),
                VehiculoORM.tenant_id == int(t_id),
            )
            orm_vehicle = s.scalars(stmt).first()
            if orm_vehicle is None:
                return vehicle

            orm_vehicle.id_modelo = int(vehicle.id_modelo)
            orm_vehicle.id_categoria = int(vehicle.id_categoria)
            orm_vehicle.placa = vehicle.placa.strip().upper()
            orm_vehicle.vin = vehicle.vin.strip().upper()
            orm_vehicle.color = vehicle.color.strip()
            orm_vehicle.kilometraje_actual = int(vehicle.kilometraje_actual)
            orm_vehicle.nivel_combustible_actual = Decimal(
                str(vehicle.nivel_combustible_actual)
            )
            orm_vehicle.estado = estado_str
            orm_vehicle.km_proximo_mantenimiento = int(vehicle.km_proximo_mantenimiento)
            orm_vehicle.activo = bool(vehicle.activo)
            s.flush()
            s.refresh(orm_vehicle)
            logger.info(
                "Vehículo actualizado exitosamente ID %s: %s",
                vehicle.id_vehiculo,
                vehicle.placa,
            )
            return orm_vehicle.to_domain()

    def update_status(
        self, id_vehiculo: int, new_status: VehicleStatus, conn: Any = None
    ) -> bool:
        """Modifica exclusivamente el estado operativo de un vehículo.

        Args:
            id_vehiculo (int): Identificador primario del vehículo.
            new_status (VehicleStatus): Nuevo estado operativo.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            bool: ``True`` si se actualizó el vehículo, ``False`` si no se encontró.
        """
        t_id = self.current_tenant_id
        status_val = (
            new_status.value
            if isinstance(new_status, VehicleStatus)
            else str(new_status)
        )
        with self.session_scope(conn) as s:
            stmt = select(VehiculoORM).where(
                VehiculoORM.id_vehiculo == int(id_vehiculo),
                VehiculoORM.tenant_id == int(t_id),
            )
            orm_vehicle = s.scalars(stmt).first()
            if orm_vehicle is None:
                return False
            orm_vehicle.estado = status_val
            s.flush()
            logger.info(
                "Estado del vehículo ID %s actualizado a '%s'", id_vehiculo, status_val
            )
            return True

    def update_delivery_state(
        self,
        id_vehiculo: int,
        kilometraje: int,
        combustible: Decimal,
        new_status: VehicleStatus,
        conn: Any = None,
    ) -> bool:
        """Actualiza odómetro, nivel de combustible y estado tras entrega o devolución.

        Args:
            id_vehiculo (int): Identificador primario del vehículo.
            kilometraje (int): Nuevo kilometraje registrado.
            combustible (Decimal): Nivel de combustible entre ``0.00`` y ``1.00``.
            new_status (VehicleStatus): Nuevo estado operativo del vehículo.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            bool: ``True`` si se actualizó el registro, ``False`` en caso contrario.
        """
        t_id = self.current_tenant_id
        status_val = (
            new_status.value
            if isinstance(new_status, VehicleStatus)
            else str(new_status)
        )
        with self.session_scope(conn) as s:
            stmt = select(VehiculoORM).where(
                VehiculoORM.id_vehiculo == int(id_vehiculo),
                VehiculoORM.tenant_id == int(t_id),
            )
            orm_vehicle = s.scalars(stmt).first()
            if orm_vehicle is None:
                return False
            orm_vehicle.kilometraje_actual = int(kilometraje)
            orm_vehicle.nivel_combustible_actual = Decimal(str(combustible))
            orm_vehicle.estado = status_val
            s.flush()
            logger.info(
                "Vehículo ID %s actualizado en entrega: km=%s, comb=%s, estado=%s",
                id_vehiculo,
                kilometraje,
                combustible,
                status_val,
            )
            return True

    def update_mileage_and_fuel(
        self,
        id_vehiculo: int,
        kilometraje: int,
        combustible: Decimal,
        conn: Any = None,
    ) -> bool:
        """Actualiza el kilometraje actual y el nivel de combustible de un vehículo.

        Args:
            id_vehiculo (int): Identificador primario del vehículo.
            kilometraje (int): Nuevo kilometraje en el odómetro.
            combustible (Decimal): Nivel de combustible entre ``0.00`` y ``1.00``.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            bool: ``True`` si se actualizó el vehículo, ``False`` si no existía.
        """
        t_id = self.current_tenant_id
        with self.session_scope(conn) as s:
            stmt = select(VehiculoORM).where(
                VehiculoORM.id_vehiculo == int(id_vehiculo),
                VehiculoORM.tenant_id == int(t_id),
            )
            orm_vehicle = s.scalars(stmt).first()
            if orm_vehicle is None:
                return False
            orm_vehicle.kilometraje_actual = int(kilometraje)
            orm_vehicle.nivel_combustible_actual = Decimal(str(combustible))
            s.flush()
            return True

    def update_maintenance_release(
        self,
        id_vehiculo: int,
        nuevo_km_proximo_mantenimiento: Optional[int] = None,
        conn: Any = None,
    ) -> bool:
        """Restaura un vehículo de taller a ``DISPONIBLE`` y actualiza su próximo km de mantenimiento.

        Args:
            id_vehiculo (int): Identificador primario del vehículo.
            nuevo_km_proximo_mantenimiento (Optional[int]): Nuevo umbral de km para mantenimiento.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            bool: ``True`` si se actualizó el vehículo, ``False`` en caso contrario.
        """
        t_id = self.current_tenant_id
        with self.session_scope(conn) as s:
            stmt = select(VehiculoORM).where(
                VehiculoORM.id_vehiculo == int(id_vehiculo),
                VehiculoORM.tenant_id == int(t_id),
            )
            orm_vehicle = s.scalars(stmt).first()
            if orm_vehicle is None:
                return False
            orm_vehicle.estado = VehicleStatus.DISPONIBLE.value
            if nuevo_km_proximo_mantenimiento is not None:
                orm_vehicle.km_proximo_mantenimiento = int(
                    nuevo_km_proximo_mantenimiento
                )
            s.flush()
            logger.info(
                "Vehículo ID %s liberado de taller: estado=DISPONIBLE, km_proximo=%s",
                id_vehiculo,
                nuevo_km_proximo_mantenimiento,
            )
            return True

    def soft_delete(self, id_vehiculo: int, conn: Any = None) -> bool:
        """Desactiva lógicamente un vehículo y cambia su estado a ``DE_BAJA``.

        Args:
            id_vehiculo (int): Identificador primario del vehículo.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            bool: ``True`` si fue desactivado, ``False`` si no existía.
        """
        t_id = self.current_tenant_id
        with self.session_scope(conn) as s:
            stmt = select(VehiculoORM).where(
                VehiculoORM.id_vehiculo == int(id_vehiculo),
                VehiculoORM.tenant_id == int(t_id),
            )
            orm_vehicle = s.scalars(stmt).first()
            if orm_vehicle is None:
                return False
            orm_vehicle.activo = False
            orm_vehicle.estado = VehicleStatus.DE_BAJA.value
            s.flush()
            return True

    def deactivate(self, id_vehiculo: int, conn: Any = None) -> bool:
        """Desactiva lógicamente un vehículo marcándolo como ``DE_BAJA`` (alias de ``soft_delete``).

        Args:
            id_vehiculo (int): Identificador primario del vehículo.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            bool: ``True`` si el vehículo fue dado de baja lógicamente.
        """
        return self.soft_delete(id_vehiculo, conn=conn)

    def delete(self, id_vehiculo: int, conn: Any = None) -> bool:
        """Elimina físicamente el vehículo de la base de datos si no posee restricciones.

        Args:
            id_vehiculo (int): Identificador primario del vehículo.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            bool: ``True`` si se eliminó el vehículo, ``False`` si no existía.
        """
        t_id = self.current_tenant_id
        with self.session_scope(conn) as s:
            stmt = select(VehiculoORM).where(
                VehiculoORM.id_vehiculo == int(id_vehiculo),
                VehiculoORM.tenant_id == int(t_id),
            )
            orm_vehicle = s.scalars(stmt).first()
            if orm_vehicle is None:
                return False
            s.delete(orm_vehicle)
            s.flush()
            return True

    def has_active_commitments(self, id_vehiculo: int, conn: Any = None) -> bool:
        """Verifica si el vehículo está asignado a contratos o reservas vigentes.

        Args:
            id_vehiculo (int): Identificador primario del vehículo.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            bool: ``True`` si tiene contratos o reservas activas.
        """
        t_id = self.current_tenant_id
        with self.session_scope(conn) as s:
            active_contracts = (
                s.scalar(
                    select(func.count())
                    .select_from(ContratoORM)
                    .where(
                        ContratoORM.id_vehiculo == int(id_vehiculo),
                        ContratoORM.tenant_id == int(t_id),
                        ContratoORM.estado.in_(
                            ("ACTIVO", "EN_INSPECCION", "EN_LIQUIDACION")
                        ),
                    )
                )
                or 0
            )
            active_reservations = (
                s.scalar(
                    select(func.count())
                    .select_from(ReservaORM)
                    .where(
                        ReservaORM.id_vehiculo == int(id_vehiculo),
                        ReservaORM.tenant_id == int(t_id),
                        ReservaORM.estado.in_(("PENDIENTE", "CONFIRMADA")),
                    )
                )
                or 0
            )
            return (int(active_contracts) + int(active_reservations)) > 0

    def has_any_history(self, id_vehiculo: int, conn: Any = None) -> bool:
        """Verifica si el vehículo posee historial en contratos, reservas o mantenimientos.

        Args:
            id_vehiculo (int): Identificador primario del vehículo.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            bool: ``True`` si tiene historial operativo registrado.
        """
        t_id = self.current_tenant_id
        with self.session_scope(conn) as s:
            c_count = (
                s.scalar(
                    select(func.count())
                    .select_from(ContratoORM)
                    .where(
                        ContratoORM.id_vehiculo == int(id_vehiculo),
                        ContratoORM.tenant_id == int(t_id),
                    )
                )
                or 0
            )
            r_count = (
                s.scalar(
                    select(func.count())
                    .select_from(ReservaORM)
                    .where(
                        ReservaORM.id_vehiculo == int(id_vehiculo),
                        ReservaORM.tenant_id == int(t_id),
                    )
                )
                or 0
            )
            m_count = (
                s.scalar(
                    select(func.count())
                    .select_from(MantenimientoORM)
                    .where(
                        MantenimientoORM.id_vehiculo == int(id_vehiculo),
                        MantenimientoORM.tenant_id == int(t_id),
                    )
                )
                or 0
            )
            return (int(c_count) + int(r_count) + int(m_count)) > 0

    # ------------------------------------------------------------------------
    # Consultas y Operaciones de Catálogos (Marcas, Modelos, Categorías)
    # ------------------------------------------------------------------------

    def list_brands(self, conn: Any = None) -> List[Brand]:
        """Lista todas las marcas automotrices registradas ordenadas alfabéticamente.

        Args:
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            List[Brand]: Lista de marcas automotrices.
        """
        with self.session_scope(conn) as s:
            stmt = select(MarcaORM).order_by(MarcaORM.nombre.asc())
            rows = s.scalars(stmt).all()
            return [r.to_domain() for r in rows]

    def create_brand(self, nombre: str, conn: Any = None) -> Brand:
        """Registra una nueva marca automotriz en el catálogo global.

        Args:
            nombre (str): Nombre único de la marca automotriz.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            Brand: Marca creada con su ``id_marca`` asignado.
        """
        with self.session_scope(conn) as s:
            orm_brand = MarcaORM(nombre=nombre.strip())
            s.add(orm_brand)
            s.flush()
            return orm_brand.to_domain()

    def list_models(
        self, id_marca: Optional[int] = None, conn: Any = None
    ) -> List[VehicleModel]:
        """Lista los modelos de vehículos, opcionalmente filtrados por marca.

        Args:
            id_marca (Optional[int]): Identificador opcional de marca para filtrar.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            List[VehicleModel]: Lista de modelos con nombre de marca resuelto.
        """
        with self.session_scope(conn) as s:
            stmt = select(ModeloORM).join(
                MarcaORM, ModeloORM.id_marca == MarcaORM.id_marca
            )
            if id_marca:
                stmt = stmt.where(ModeloORM.id_marca == int(id_marca)).order_by(
                    ModeloORM.nombre.asc(), ModeloORM.anio.desc()
                )
            else:
                stmt = stmt.order_by(
                    MarcaORM.nombre.asc(),
                    ModeloORM.nombre.asc(),
                    ModeloORM.anio.desc(),
                )
            rows = s.scalars(stmt).all()
            return [r.to_domain() for r in rows]

    def create_model(self, model: VehicleModel, conn: Any = None) -> VehicleModel:
        """Registra un nuevo modelo de vehículo en el catálogo global.

        Args:
            model (VehicleModel): Entidad ``VehicleModel`` a registrar.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            VehicleModel: Modelo creado con su ``id_modelo`` asignado.
        """
        with self.session_scope(conn) as s:
            orm_model = ModeloORM(
                id_marca=int(model.id_marca),
                nombre=model.nombre.strip(),
                anio=int(model.anio),
                tipo_transmision=model.tipo_transmision.strip().upper(),
                capacidad_pasajeros=int(model.capacidad_pasajeros),
            )
            s.add(orm_model)
            s.flush()
            s.refresh(orm_model)
            return orm_model.to_domain()

    def list_categories(self, conn: Any = None) -> List[VehicleCategory]:
        """Lista todas las categorías tarifarias de vehículos de la agencia activa.

        Args:
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            List[VehicleCategory]: Lista de categorías ordenadas por tarifa diaria ascendente.
        """
        t_id = self.current_tenant_id
        with self.session_scope(conn) as s:
            stmt = (
                select(CategoriaVehiculoORM)
                .where(CategoriaVehiculoORM.tenant_id == int(t_id))
                .order_by(CategoriaVehiculoORM.tarifa_base_diaria.asc())
            )
            rows = s.scalars(stmt).all()
            return [r.to_domain() for r in rows]

    def get_category_by_id(
        self, id_categoria: int, conn: Any = None
    ) -> Optional[VehicleCategory]:
        """Obtiene una categoría de vehículo por su identificador primario en la agencia activa.

        Args:
            id_categoria (int): Identificador primario de la categoría.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            Optional[VehicleCategory]: Categoría encontrada o ``None``.
        """
        t_id = self.current_tenant_id
        with self.session_scope(conn) as s:
            stmt = select(CategoriaVehiculoORM).where(
                CategoriaVehiculoORM.id_categoria == int(id_categoria),
                CategoriaVehiculoORM.tenant_id == int(t_id),
            )
            obj = s.scalars(stmt).first()
            return obj.to_domain() if obj else None

    def count_by_status(self, conn: Any = None) -> dict[str, int]:
        """Agrupa y cuenta los vehículos activos de la agencia según su estado operativo.

        Args:
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            dict[str, int]: Diccionario ``{estado: cantidad}`` para todos los estados de flota.
        """
        t_id = self.current_tenant_id
        counts: dict[str, int] = {status.value: 0 for status in VehicleStatus}
        with self.session_scope(conn) as s:
            stmt = (
                select(VehiculoORM.estado, func.count(VehiculoORM.id_vehiculo))
                .where(
                    VehiculoORM.tenant_id == int(t_id),
                    VehiculoORM.activo.is_(True),
                )
                .group_by(VehiculoORM.estado)
            )
            for estado_str, total in s.execute(stmt).all():
                counts[str(estado_str)] = int(total)
        return counts
