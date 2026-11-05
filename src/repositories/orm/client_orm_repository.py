"""Repositorio SQLAlchemy 2.0 ORM para la entidad Cliente y Licencias de Conducir."""

from typing import Any, List, Optional

from sqlalchemy import func, or_, select

from src.core.logger import get_logger
from src.database.orm_models import (
    ClienteORM,
    ContratoORM,
    LicenciaConducirORM,
    ReservaORM,
)
from src.domain.enums import ClientStatus, ClientType
from src.domain.models import Client, DriverLicense
from src.repositories.orm.base_orm_repository import BaseORMRepository

logger = get_logger(__name__)


class ClientORMRepository(BaseORMRepository[Client]):
    """Operaciones de persistencia mediante SQLAlchemy 2.0 ORM para clientes y licencias de conducir."""

    def get_by_id(self, id_cliente: int, conn: Any = None) -> Optional[Client]:
        """Obtiene un cliente por su identificador primario dentro de la agencia activa, incluyendo licencia.

        Args:
            id_cliente (int): Identificador primario del cliente.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            Optional[Client]: Objeto ``Client`` con su ``DriverLicense`` anidada, o ``None``.
        """
        t_id = self.current_tenant_id
        with self.session_scope(conn) as s:
            stmt = select(ClienteORM).where(
                ClienteORM.id_cliente == int(id_cliente),
                ClienteORM.tenant_id == int(t_id),
            )
            obj = s.scalars(stmt).first()
            return obj.to_domain() if obj else None

    def get_by_identificacion(
        self, identificacion: str, conn: Any = None
    ) -> Optional[Client]:
        """Obtiene un cliente por su número de cédula, pasaporte o RUC dentro de la agencia activa.

        Args:
            identificacion (str): Documento de identificación del cliente.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            Optional[Client]: Objeto ``Client`` si existe, o ``None``.
        """
        t_id = self.current_tenant_id
        clean_id = identificacion.strip()
        with self.session_scope(conn) as s:
            stmt = select(ClienteORM).where(
                ClienteORM.identificacion == clean_id,
                ClienteORM.tenant_id == int(t_id),
            )
            obj = s.scalars(stmt).first()
            return obj.to_domain() if obj else None

    def get_by_email(self, email: str, conn: Any = None) -> Optional[Client]:
        """Obtiene un cliente por su dirección de correo electrónico dentro de la agencia activa.

        Args:
            email (str): Correo electrónico del cliente.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            Optional[Client]: Entidad ``Client`` si se encuentra, o ``None``.
        """
        t_id = self.current_tenant_id
        clean_email = email.strip().lower()
        with self.session_scope(conn) as s:
            stmt = select(ClienteORM).where(
                func.lower(ClienteORM.email) == clean_email,
                ClienteORM.tenant_id == int(t_id),
            )
            obj = s.scalars(stmt).first()
            return obj.to_domain() if obj else None

    def get_license_by_number(
        self,
        numero_licencia: str,
        exclude_client_id: Optional[int] = None,
        conn: Any = None,
    ) -> Optional[DriverLicense]:
        """Busca una licencia de conducir por su número único en la agencia activa.

        Args:
            numero_licencia (str): Número de licencia de conducir a verificar.
            exclude_client_id (Optional[int]): ID de cliente a excluir de la búsqueda (para ediciones).
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            Optional[DriverLicense]: Licencia de conducir encontrada o ``None``.
        """
        t_id = self.current_tenant_id
        clean_num = numero_licencia.strip()
        with self.session_scope(conn) as s:
            stmt = select(LicenciaConducirORM).where(
                func.upper(LicenciaConducirORM.numero_licencia) == clean_num.upper(),
                LicenciaConducirORM.tenant_id == int(t_id),
            )
            if exclude_client_id is not None:
                stmt = stmt.where(
                    LicenciaConducirORM.id_cliente != int(exclude_client_id)
                )
            obj = s.scalars(stmt).first()
            return obj.to_domain() if obj else None

    def list_all(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        conn: Any = None,
    ) -> List[Client]:
        """Lista los clientes de la agencia activa con soporte para búsqueda textual y filtro de estado.

        Args:
            search (Optional[str]): Término de búsqueda libre sobre identificación, nombres, email o licencia.
            status (Optional[str]): Filtro opcional por estado del cliente (ej. ``ACTIVO``, ``MOROSO``).
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            List[Client]: Lista de clientes ordenados de forma descendente por ``id_cliente``.
        """
        t_id = self.current_tenant_id
        with self.session_scope(conn) as s:
            stmt = (
                select(ClienteORM)
                .outerjoin(
                    LicenciaConducirORM,
                    (ClienteORM.id_cliente == LicenciaConducirORM.id_cliente)
                    & (ClienteORM.tenant_id == LicenciaConducirORM.tenant_id),
                )
                .where(ClienteORM.tenant_id == int(t_id))
            )

            if status and status.upper() != "TODOS":
                stmt = stmt.where(ClienteORM.estado_cliente == status.upper())

            if search and search.strip():
                term = f"%{search.strip()}%"
                stmt = stmt.where(
                    or_(
                        ClienteORM.identificacion.ilike(term),
                        ClienteORM.nombres.ilike(term),
                        ClienteORM.apellidos.ilike(term),
                        ClienteORM.email.ilike(term),
                        ClienteORM.telefono.ilike(term),
                        LicenciaConducirORM.numero_licencia.ilike(term),
                    )
                )

            stmt = stmt.order_by(ClienteORM.id_cliente.desc())
            rows = s.scalars(stmt).unique().all()
            return [r.to_domain() for r in rows]

    def create(
        self,
        client: Client,
        license: Optional[DriverLicense] = None,
        conn: Any = None,
    ) -> Client:
        """Inserta un nuevo cliente y su licencia de conducir asociada de forma atómica.

        Args:
            client (Client): Entidad de dominio ``Client`` a persistir.
            license (Optional[DriverLicense]): Licencia de conducir opcional (o vía ``client.licencia``).
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            Client: Entidad ``Client`` creada con sus identificadores asignados.
        """
        target_tenant = self.current_tenant_id
        lic_data = license if license is not None else client.licencia

        tipo_str = (
            client.tipo_persona.value
            if isinstance(client.tipo_persona, ClientType)
            else str(client.tipo_persona)
        )
        estado_str = (
            client.estado_cliente.value
            if isinstance(client.estado_cliente, ClientStatus)
            else str(client.estado_cliente)
        )

        with self.session_scope(conn) as s:
            orm_client = ClienteORM(
                tenant_id=int(target_tenant),
                tipo_persona=tipo_str,
                identificacion=client.identificacion.strip(),
                nombres=client.nombres.strip(),
                apellidos=client.apellidos.strip(),
                telefono=client.telefono.strip(),
                email=client.email.strip().lower(),
                direccion=client.direccion.strip(),
                estado_cliente=estado_str,
            )
            s.add(orm_client)
            s.flush()

            if lic_data and lic_data.numero_licencia and lic_data.numero_licencia.strip():
                orm_lic = LicenciaConducirORM(
                    tenant_id=int(target_tenant),
                    id_cliente=int(orm_client.id_cliente),
                    numero_licencia=lic_data.numero_licencia.strip(),
                    categoria_licencia=lic_data.categoria_licencia.strip(),
                    fecha_emision=lic_data.fecha_emision,
                    fecha_vencimiento=lic_data.fecha_vencimiento,
                    pais_emision=(
                        lic_data.pais_emision.strip()
                        if lic_data.pais_emision
                        else "Nicaragua"
                    ),
                )
                s.add(orm_lic)
                s.flush()

            s.refresh(orm_client)
            created = orm_client.to_domain()
            client.id_cliente = created.id_cliente
            client.tenant_id = created.tenant_id
            client.fecha_registro = created.fecha_registro
            client.licencia = created.licencia
            if lic_data and created.licencia:
                lic_data.id_licencia = created.licencia.id_licencia
                lic_data.id_cliente = created.id_cliente
                lic_data.tenant_id = created.tenant_id

            logger.info(
                "Cliente creado exitosamente con ID %s: %s %s",
                created.id_cliente,
                created.nombres,
                created.apellidos,
            )
            return created

    def update(
        self,
        client: Client,
        license: Optional[DriverLicense] = None,
        conn: Any = None,
    ) -> Client:
        """Actualiza los datos de un cliente existente y su licencia de conducir asociada.

        Args:
            client (Client): Entidad ``Client`` con los datos actualizados.
            license (Optional[DriverLicense]): Licencia de conducir opcional (o vía ``client.licencia``).
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            Client: Entidad ``Client`` actualizada.
        """
        target_tenant = self.current_tenant_id
        lic_data = license if license is not None else client.licencia

        tipo_str = (
            client.tipo_persona.value
            if isinstance(client.tipo_persona, ClientType)
            else str(client.tipo_persona)
        )
        estado_str = (
            client.estado_cliente.value
            if isinstance(client.estado_cliente, ClientStatus)
            else str(client.estado_cliente)
        )

        with self.session_scope(conn) as s:
            stmt = select(ClienteORM).where(
                ClienteORM.id_cliente == int(client.id_cliente),
                ClienteORM.tenant_id == int(target_tenant),
            )
            orm_client = s.scalars(stmt).first()
            if orm_client is None:
                return client

            orm_client.tipo_persona = tipo_str
            orm_client.identificacion = client.identificacion.strip()
            orm_client.nombres = client.nombres.strip()
            orm_client.apellidos = client.apellidos.strip()
            orm_client.telefono = client.telefono.strip()
            orm_client.email = client.email.strip().lower()
            orm_client.direccion = client.direccion.strip()
            orm_client.estado_cliente = estado_str
            s.flush()

            if lic_data and lic_data.numero_licencia and lic_data.numero_licencia.strip():
                existing_lic = orm_client.licencia
                if existing_lic is not None:
                    existing_lic.numero_licencia = lic_data.numero_licencia.strip()
                    existing_lic.categoria_licencia = lic_data.categoria_licencia.strip()
                    existing_lic.fecha_emision = lic_data.fecha_emision
                    existing_lic.fecha_vencimiento = lic_data.fecha_vencimiento
                    existing_lic.pais_emision = (
                        lic_data.pais_emision.strip()
                        if lic_data.pais_emision
                        else "Nicaragua"
                    )
                    s.flush()
                else:
                    new_lic = LicenciaConducirORM(
                        tenant_id=int(target_tenant),
                        id_cliente=int(orm_client.id_cliente),
                        numero_licencia=lic_data.numero_licencia.strip(),
                        categoria_licencia=lic_data.categoria_licencia.strip(),
                        fecha_emision=lic_data.fecha_emision,
                        fecha_vencimiento=lic_data.fecha_vencimiento,
                        pais_emision=(
                            lic_data.pais_emision.strip()
                            if lic_data.pais_emision
                            else "Nicaragua"
                        ),
                    )
                    s.add(new_lic)
                    s.flush()

            s.refresh(orm_client)
            updated = orm_client.to_domain()
            client.licencia = updated.licencia
            if lic_data and updated.licencia:
                lic_data.id_licencia = updated.licencia.id_licencia
            logger.info("Cliente actualizado exitosamente ID %s", client.id_cliente)
            return updated

    def update_status(
        self,
        id_cliente: int,
        new_status: Optional[ClientStatus] = None,
        conn: Any = None,
        *,
        status: Optional[ClientStatus] = None,
    ) -> bool:
        """Actualiza el estado comercial de un cliente (``ACTIVO``, ``MOROSO``, ``VETADO``).

        Args:
            id_cliente (int): Identificador primario del cliente.
            new_status (Optional[ClientStatus]): Nuevo estado del cliente.
            conn (Any): Sesión ORM compartida opcional.
            status (Optional[ClientStatus]): Alias por palabra clave para ``new_status``.

        Returns:
            bool: ``True`` si se actualizó el registro, ``False`` si no se encontró.
        """
        target_status = new_status if new_status is not None else status
        val = (
            target_status.value
            if isinstance(target_status, ClientStatus)
            else str(target_status)
        )
        t_id = self.current_tenant_id
        with self.session_scope(conn) as s:
            stmt = select(ClienteORM).where(
                ClienteORM.id_cliente == int(id_cliente),
                ClienteORM.tenant_id == int(t_id),
            )
            orm_client = s.scalars(stmt).first()
            if orm_client is None:
                return False
            orm_client.estado_cliente = val
            s.flush()
            return True

    def delete(self, id_cliente: int, conn: Any = None) -> bool:
        """Elimina físicamente un cliente y su licencia en cascada de la agencia activa.

        Args:
            id_cliente (int): Identificador primario del cliente a eliminar.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            bool: ``True`` si se eliminó el cliente, ``False`` si no existía.
        """
        t_id = self.current_tenant_id
        with self.session_scope(conn) as s:
            stmt = select(ClienteORM).where(
                ClienteORM.id_cliente == int(id_cliente),
                ClienteORM.tenant_id == int(t_id),
            )
            orm_client = s.scalars(stmt).first()
            if orm_client is None:
                return False
            s.delete(orm_client)
            s.flush()
            return True

    def has_active_commitments(self, id_cliente: int, conn: Any = None) -> bool:
        """Verifica si el cliente tiene contratos o reservas activos o pendientes en la agencia.

        Args:
            id_cliente (int): Identificador primario del cliente.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            bool: ``True`` si existen operaciones activas vinculadas al cliente.
        """
        t_id = self.current_tenant_id
        with self.session_scope(conn) as s:
            active_contracts = (
                s.scalar(
                    select(func.count())
                    .select_from(ContratoORM)
                    .where(
                        ContratoORM.id_cliente == int(id_cliente),
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
                        ReservaORM.id_cliente == int(id_cliente),
                        ReservaORM.tenant_id == int(t_id),
                        ReservaORM.estado.in_(("PENDIENTE", "CONFIRMADA")),
                    )
                )
                or 0
            )
            return (int(active_contracts) + int(active_reservations)) > 0

    def has_active_operations(self, id_cliente: int, conn: Any = None) -> bool:
        """Verifica si el cliente posee operaciones activas (alias compatible con ``has_active_commitments``).

        Args:
            id_cliente (int): Identificador primario del cliente.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            bool: ``True`` si tiene reservas o contratos en curso.
        """
        return self.has_active_commitments(id_cliente, conn=conn)

    def has_any_history(self, id_cliente: int, conn: Any = None) -> bool:
        """Verifica si el cliente tiene algún registro histórico en contratos o reservas.

        Args:
            id_cliente (int): Identificador primario del cliente.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            bool: ``True`` si cuenta con historial operativo registrado.
        """
        t_id = self.current_tenant_id
        with self.session_scope(conn) as s:
            total_contracts = (
                s.scalar(
                    select(func.count())
                    .select_from(ContratoORM)
                    .where(
                        ContratoORM.id_cliente == int(id_cliente),
                        ContratoORM.tenant_id == int(t_id),
                    )
                )
                or 0
            )
            total_reservations = (
                s.scalar(
                    select(func.count())
                    .select_from(ReservaORM)
                    .where(
                        ReservaORM.id_cliente == int(id_cliente),
                        ReservaORM.tenant_id == int(t_id),
                    )
                )
                or 0
            )
            return (int(total_contracts) + int(total_reservations)) > 0

    def count_active_clients(self, conn: Any = None) -> int:
        """Cuenta el total de clientes con estado ``ACTIVO`` en la agencia actual.

        Args:
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            int: Cantidad de clientes activos.
        """
        t_id = self.current_tenant_id
        with self.session_scope(conn) as s:
            stmt = (
                select(func.count())
                .select_from(ClienteORM)
                .where(
                    ClienteORM.tenant_id == int(t_id),
                    ClienteORM.estado_cliente == ClientStatus.ACTIVO.value,
                )
            )
            return int(s.scalar(stmt) or 0)
