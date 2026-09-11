"""Repositorio de acceso a datos para la entidad Cliente y Licencias de Conducir (DAL)."""

from typing import Any, List, Optional
from src.core.logger import get_logger
from src.domain.enums import ClientStatus, ClientType
from src.domain.models import Client, DriverLicense
from src.repositories.base_repository import BaseRepository

logger = get_logger(__name__)


class ClientRepository(BaseRepository[Client]):
    """Operaciones de persistencia para la gestión integral de clientes y licencias."""

    @staticmethod
    def _map_row_to_client(row: dict) -> Client:
        """Mapea una fila de base de datos con posible JOIN a un objeto Client con DriverLicense."""
        license_obj: Optional[DriverLicense] = None
        if row.get("id_licencia") is not None:
            license_obj = DriverLicense(
                id_licencia=row["id_licencia"],
                id_cliente=row["id_cliente"],
                numero_licencia=row["numero_licencia"],
                categoria_licencia=row["categoria_licencia"],
                fecha_emision=row["fecha_emision"],
                fecha_vencimiento=row["fecha_vencimiento"],
                pais_emision=row.get("pais_emision", "Nicaragua"),
            )

        return Client(
            id_cliente=row["id_cliente"],
            tipo_persona=ClientType(row["tipo_persona"]),
            identificacion=row["identificacion"],
            nombres=row["nombres"],
            apellidos=row["apellidos"],
            telefono=row["telefono"],
            email=row["email"],
            direccion=row["direccion"],
            estado_cliente=ClientStatus(row["estado_cliente"]),
            fecha_registro=row.get("fecha_registro"),
            licencia=license_obj,
        )

    def get_by_id(self, id_cliente: int, conn: Any = None) -> Optional[Client]:
        """Obtiene un cliente por su ID primario, incluyendo su licencia si existe."""
        query = """
            SELECT 
                c.id_cliente,
                c.tipo_persona,
                c.identificacion,
                c.nombres,
                c.apellidos,
                c.telefono,
                c.email,
                c.direccion,
                c.estado_cliente,
                c.fecha_registro,
                l.id_licencia,
                l.numero_licencia,
                l.categoria_licencia,
                l.fecha_emision,
                l.fecha_vencimiento,
                l.pais_emision
            FROM clientes c
            LEFT JOIN licencias_conducir l ON c.id_cliente = l.id_cliente
            WHERE c.id_cliente = %s;
        """
        row = self.execute_query_one(query, (id_cliente,), conn=conn)
        return self._map_row_to_client(row) if row else None

    def get_by_identificacion(self, identificacion: str, conn: Any = None) -> Optional[Client]:
        """Obtiene un cliente por su número de cédula o RUC."""
        query = """
            SELECT 
                c.id_cliente,
                c.tipo_persona,
                c.identificacion,
                c.nombres,
                c.apellidos,
                c.telefono,
                c.email,
                c.direccion,
                c.estado_cliente,
                c.fecha_registro,
                l.id_licencia,
                l.numero_licencia,
                l.categoria_licencia,
                l.fecha_emision,
                l.fecha_vencimiento,
                l.pais_emision
            FROM clientes c
            LEFT JOIN licencias_conducir l ON c.id_cliente = l.id_cliente
            WHERE c.identificacion = %s;
        """
        row = self.execute_query_one(query, (identificacion.strip(),), conn=conn)
        return self._map_row_to_client(row) if row else None

    def get_by_email(self, email: str, conn: Any = None) -> Optional[Client]:
        """Obtiene un cliente por su correo electrónico."""
        query = """
            SELECT 
                c.id_cliente,
                c.tipo_persona,
                c.identificacion,
                c.nombres,
                c.apellidos,
                c.telefono,
                c.email,
                c.direccion,
                c.estado_cliente,
                c.fecha_registro,
                l.id_licencia,
                l.numero_licencia,
                l.categoria_licencia,
                l.fecha_emision,
                l.fecha_vencimiento,
                l.pais_emision
            FROM clientes c
            LEFT JOIN licencias_conducir l ON c.id_cliente = l.id_cliente
            WHERE LOWER(c.email) = LOWER(%s);
        """
        row = self.execute_query_one(query, (email.strip(),), conn=conn)
        return self._map_row_to_client(row) if row else None

    def list_all(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        conn: Any = None,
    ) -> List[Client]:
        """Lista clientes con soporte para búsqueda textual y filtro de estado."""
        conditions = []
        params: List[Any] = []

        if status and status.upper() != "TODOS":
            conditions.append("c.estado_cliente = %s")
            params.append(status.upper())

        if search and search.strip():
            term = f"%{search.strip()}%"
            conditions.append("""
                (c.identificacion ILIKE %s OR 
                 c.nombres ILIKE %s OR 
                 c.apellidos ILIKE %s OR 
                 c.email ILIKE %s OR 
                 c.telefono ILIKE %s OR
                 l.numero_licencia ILIKE %s)
            """)
            params.extend([term, term, term, term, term, term])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT 
                c.id_cliente,
                c.tipo_persona,
                c.identificacion,
                c.nombres,
                c.apellidos,
                c.telefono,
                c.email,
                c.direccion,
                c.estado_cliente,
                c.fecha_registro,
                l.id_licencia,
                l.numero_licencia,
                l.categoria_licencia,
                l.fecha_emision,
                l.fecha_vencimiento,
                l.pais_emision
            FROM clientes c
            LEFT JOIN licencias_conducir l ON c.id_cliente = l.id_cliente
            {where_clause}
            ORDER BY c.id_cliente DESC;
        """
        rows = self.execute_query(query, tuple(params) if params else None, conn=conn)
        return [self._map_row_to_client(r) for r in rows]

    def create(
        self,
        client: Client,
        license: Optional[DriverLicense] = None,
        conn: Any = None,
    ) -> Client:
        """Inserta un nuevo cliente y su licencia asociada de forma atómica."""
        query_client = """
            INSERT INTO clientes (
                tipo_persona,
                identificacion,
                nombres,
                apellidos,
                telefono,
                email,
                direccion,
                estado_cliente
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_cliente, fecha_registro;
        """
        params_client = (
            client.tipo_persona.value if isinstance(client.tipo_persona, ClientType) else str(client.tipo_persona),
            client.identificacion.strip(),
            client.nombres.strip(),
            client.apellidos.strip(),
            client.telefono.strip(),
            client.email.strip().lower(),
            client.direccion.strip(),
            client.estado_cliente.value if isinstance(client.estado_cliente, ClientStatus) else str(client.estado_cliente),
        )

        row = self.execute_query_one(query_client, params_client, conn=conn)
        if not row:
            raise RuntimeError("No se pudo obtener el ID del cliente generado.")

        client.id_cliente = row["id_cliente"]
        client.fecha_registro = row["fecha_registro"]

        if license and license.numero_licencia.strip():
            license.id_cliente = client.id_cliente
            query_license = """
                INSERT INTO licencias_conducir (
                    id_cliente,
                    numero_licencia,
                    categoria_licencia,
                    fecha_emision,
                    fecha_vencimiento,
                    pais_emision
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id_licencia;
            """
            params_license = (
                client.id_cliente,
                license.numero_licencia.strip(),
                license.categoria_licencia.strip(),
                license.fecha_emision,
                license.fecha_vencimiento,
                license.pais_emision.strip() if license.pais_emision else "Nicaragua",
            )
            lic_row = self.execute_query_one(query_license, params_license, conn=conn)
            if lic_row:
                license.id_licencia = lic_row["id_licencia"]
            client.licencia = license

        logger.info("Cliente creado exitosamente con ID %s: %s %s", client.id_cliente, client.nombres, client.apellidos)
        return client

    def update(
        self,
        client: Client,
        license: Optional[DriverLicense] = None,
        conn: Any = None,
    ) -> Client:
        """Actualiza un cliente existente y sus datos de licencia de conducir."""
        query_client = """
            UPDATE clientes SET
                tipo_persona = %s,
                identificacion = %s,
                nombres = %s,
                apellidos = %s,
                telefono = %s,
                email = %s,
                direccion = %s,
                estado_cliente = %s
            WHERE id_cliente = %s;
        """
        params_client = (
            client.tipo_persona.value if isinstance(client.tipo_persona, ClientType) else str(client.tipo_persona),
            client.identificacion.strip(),
            client.nombres.strip(),
            client.apellidos.strip(),
            client.telefono.strip(),
            client.email.strip().lower(),
            client.direccion.strip(),
            client.estado_cliente.value if isinstance(client.estado_cliente, ClientStatus) else str(client.estado_cliente),
            client.id_cliente,
        )
        self.execute_non_query(query_client, params_client, conn=conn)

        if license and license.numero_licencia.strip():
            # Comprobar si ya tenía licencia registrada
            check_query = "SELECT id_licencia FROM licencias_conducir WHERE id_cliente = %s;"
            existing = self.execute_query_one(check_query, (client.id_cliente,), conn=conn)

            if existing:
                query_lic_update = """
                    UPDATE licencias_conducir SET
                        numero_licencia = %s,
                        categoria_licencia = %s,
                        fecha_emision = %s,
                        fecha_vencimiento = %s,
                        pais_emision = %s
                    WHERE id_cliente = %s;
                """
                params_lic_update = (
                    license.numero_licencia.strip(),
                    license.categoria_licencia.strip(),
                    license.fecha_emision,
                    license.fecha_vencimiento,
                    license.pais_emision.strip() if license.pais_emision else "Nicaragua",
                    client.id_cliente,
                )
                self.execute_non_query(query_lic_update, params_lic_update, conn=conn)
                license.id_licencia = existing["id_licencia"]
            else:
                query_lic_insert = """
                    INSERT INTO licencias_conducir (
                        id_cliente,
                        numero_licencia,
                        categoria_licencia,
                        fecha_emision,
                        fecha_vencimiento,
                        pais_emision
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id_licencia;
                """
                params_lic_insert = (
                    client.id_cliente,
                    license.numero_licencia.strip(),
                    license.categoria_licencia.strip(),
                    license.fecha_emision,
                    license.fecha_vencimiento,
                    license.pais_emision.strip() if license.pais_emision else "Nicaragua",
                )
                lic_row = self.execute_query_one(query_lic_insert, params_lic_insert, conn=conn)
                if lic_row:
                    license.id_licencia = lic_row["id_licencia"]

            client.licencia = license

        logger.info("Cliente actualizado exitosamente ID %s", client.id_cliente)
        return client

    def update_status(self, id_cliente: int, status: ClientStatus, conn: Any = None) -> bool:
        """Actualiza el estado de un cliente (ACTIVO, MOROSO, VETADO)."""
        query = "UPDATE clientes SET estado_cliente = %s WHERE id_cliente = %s;"
        val = status.value if isinstance(status, ClientStatus) else str(status)
        count = self.execute_non_query(query, (val, id_cliente), conn=conn)
        return count > 0

    def delete(self, id_cliente: int, conn: Any = None) -> bool:
        """Elimina físicamente un cliente (la licencia asociada se elimina en cascada)."""
        query = "DELETE FROM clientes WHERE id_cliente = %s;"
        count = self.execute_non_query(query, (id_cliente,), conn=conn)
        return count > 0

    def has_active_commitments(self, id_cliente: int, conn: Any = None) -> bool:
        """Verifica si el cliente tiene contratos o reservas activos o pendientes."""
        query = """
            SELECT 
                (SELECT COUNT(*) FROM contratos WHERE id_cliente = %s AND estado IN ('ACTIVO', 'EN_INSPECCION', 'EN_LIQUIDACION')) +
                (SELECT COUNT(*) FROM reservas WHERE id_cliente = %s AND estado IN ('PENDIENTE', 'CONFIRMADA'))
            AS total_activos;
        """
        count = self.execute_scalar(query, (id_cliente, id_cliente), conn=conn)
        return (count or 0) > 0

    def has_any_history(self, id_cliente: int, conn: Any = None) -> bool:
        """Verifica si el cliente tiene algún registro histórico en contratos o reservas."""
        query = """
            SELECT 
                (SELECT COUNT(*) FROM contratos WHERE id_cliente = %s) +
                (SELECT COUNT(*) FROM reservas WHERE id_cliente = %s)
            AS total_historial;
        """
        count = self.execute_scalar(query, (id_cliente, id_cliente), conn=conn)
        return (count or 0) > 0
