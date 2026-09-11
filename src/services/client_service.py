"""Servicio de lógica de negocio para la gestión de Clientes y Licencias (BLL)."""

import re
from typing import List, Optional
from src.core.exceptions import (
    BusinessRuleViolationError,
    DuplicateRecordError,
    RecordNotFoundError,
    ValidationError,
)
from src.core.logger import get_logger
from src.domain.enums import ClientStatus, ClientType
from src.domain.models import Client, DriverLicense
from src.repositories.client_repository import ClientRepository
from src.services.base_service import BaseService

logger = get_logger(__name__)

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


class ClientService(BaseService):
    """Servicio empresarial que orquesta validaciones, reglas de negocio y transacciones para Clientes."""

    def __init__(self, client_repo: Optional[ClientRepository] = None) -> None:
        super().__init__()
        self.client_repo = client_repo or ClientRepository(self.db)

    def _validate_client_fields(
        self,
        client: Client,
        license: Optional[DriverLicense] = None,
        is_update: bool = False,
    ) -> None:
        """Aplica validaciones estrictas sobre los datos del cliente y su licencia."""
        # 1. Campos obligatorios del cliente
        self.validate_required("Identificación", client.identificacion)
        self.validate_required("Nombres", client.nombres)
        self.validate_required("Apellidos", client.apellidos)
        self.validate_required("Teléfono", client.telefono)
        self.validate_required("Correo electrónico", client.email)
        self.validate_required("Dirección", client.direccion)

        # 2. Formato de correo electrónico
        clean_email = client.email.strip().lower()
        if not EMAIL_REGEX.match(clean_email):
            raise ValidationError(
                f"El formato del correo electrónico '{client.email}' es inválido.",
                code="INVALID_EMAIL_FORMAT",
            )

        # 3. Unicidad de Identificación (Cédula o RUC)
        existing_by_id = self.client_repo.get_by_identificacion(client.identificacion)
        if existing_by_id:
            if not is_update or existing_by_id.id_cliente != client.id_cliente:
                raise DuplicateRecordError(
                    f"Ya existe un cliente registrado con la identificación '{client.identificacion}' "
                    f"({existing_by_id.nombre_completo}).",
                    code="DUPLICATE_IDENTIFICATION",
                )

        # 4. Unicidad de Correo Electrónico
        existing_by_email = self.client_repo.get_by_email(clean_email)
        if existing_by_email:
            if not is_update or existing_by_email.id_cliente != client.id_cliente:
                raise DuplicateRecordError(
                    f"Ya existe un cliente registrado con el correo electrónico '{clean_email}'.",
                    code="DUPLICATE_EMAIL",
                )

        # 5. Validaciones de Licencia de Conducir (si se proporciona)
        if license and license.numero_licencia.strip():
            self.validate_required("Número de Licencia", license.numero_licencia)
            self.validate_required("Categoría de Licencia", license.categoria_licencia)
            self.validate_required("Fecha de Emisión", license.fecha_emision)
            self.validate_required("Fecha de Vencimiento", license.fecha_vencimiento)

            if license.fecha_vencimiento <= license.fecha_emision:
                raise ValidationError(
                    "La fecha de vencimiento de la licencia debe ser posterior a la fecha de emisión.",
                    code="INVALID_LICENSE_DATES",
                )

    def create_client(
        self,
        client: Client,
        license: Optional[DriverLicense] = None,
    ) -> Client:
        """Crea un nuevo cliente y su licencia asociada bajo una transacción ACID."""
        self._validate_client_fields(client, license, is_update=False)

        with self.run_in_transaction() as conn:
            created_client = self.client_repo.create(client, license, conn=conn)

        self.logger.info("Cliente '%s' registrado exitosamente con ID %s", created_client.nombre_completo, created_client.id_cliente)
        return created_client

    def update_client(
        self,
        client: Client,
        license: Optional[DriverLicense] = None,
    ) -> Client:
        """Actualiza la información de un cliente existente y su licencia."""
        if not client.id_cliente:
            raise ValidationError("El ID del cliente es requerido para la actualización.", code="CLIENT_ID_REQUIRED")

        existing = self.client_repo.get_by_id(client.id_cliente)
        if not existing:
            raise RecordNotFoundError(
                f"El cliente con ID {client.id_cliente} no existe en la base de datos.",
                code="CLIENT_NOT_FOUND",
            )

        self._validate_client_fields(client, license, is_update=True)

        with self.run_in_transaction() as conn:
            updated_client = self.client_repo.update(client, license, conn=conn)

        self.logger.info("Cliente ID %s actualizado con éxito.", updated_client.id_cliente)
        return updated_client

    def get_client(self, id_cliente: int) -> Client:
        """Obtiene el expediente de un cliente por su ID."""
        client = self.client_repo.get_by_id(id_cliente)
        if not client:
            raise RecordNotFoundError(
                f"No se encontró ningún cliente con el ID {id_cliente}.",
                code="CLIENT_NOT_FOUND",
            )
        return client

    def list_clients(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Client]:
        """Lista los clientes registrados con criterios de filtro y búsqueda."""
        return self.client_repo.list_all(search=search, status=status)

    def change_status(self, id_cliente: int, new_status: ClientStatus) -> None:
        """Modifica el estado comercial de un cliente (ACTIVO, MOROSO, VETADO)."""
        client = self.get_client(id_cliente)

        # Regla de Negocio: Si pasa a VETADO o MOROSO, verificar advertencias
        if new_status in (ClientStatus.MOROSO, ClientStatus.VETADO):
            if self.client_repo.has_active_commitments(id_cliente):
                self.logger.warning("El cliente ID %s pasa a %s manteniendo contratos o reservas activos.", id_cliente, new_status.value)

        with self.run_in_transaction() as conn:
            self.client_repo.update_status(id_cliente, new_status, conn=conn)

        self.logger.info("Estado del cliente ID %s cambiado de %s a %s", id_cliente, client.estado_cliente.value, new_status.value)

    def delete_client(self, id_cliente: int) -> None:
        """Elimina a un cliente validando compromisos activos y restricciones de integridad."""
        client = self.get_client(id_cliente)

        # 1. Regla: No eliminar clientes con contratos o reservas activas
        if self.client_repo.has_active_commitments(id_cliente):
            raise BusinessRuleViolationError(
                f"No es posible eliminar al cliente '{client.nombre_completo}' porque posee reservas o contratos de alquiler en curso.",
                code="CLIENT_HAS_ACTIVE_COMMITMENTS",
            )

        # 2. Regla: Si posee historial cerrado (auditoría), sugerir o requerir cambio a VETADO en lugar de destrucción física
        if self.client_repo.has_any_history(id_cliente):
            raise BusinessRuleViolationError(
                f"El cliente '{client.nombre_completo}' cuenta con registros históricos en contratos o auditoría comercial. "
                "Para preservar la integridad de los comprobantes, no se puede eliminar físicamente; cambie su estado a 'VETADO'.",
                code="CLIENT_HAS_HISTORICAL_RECORDS",
            )

        with self.run_in_transaction() as conn:
            self.client_repo.delete(id_cliente, conn=conn)

        self.logger.info("Cliente ID %s ('%s') eliminado físicamente de la base de datos.", id_cliente, client.nombre_completo)


# Instancia singleton para uso en controladores y vistas
client_service = ClientService()
