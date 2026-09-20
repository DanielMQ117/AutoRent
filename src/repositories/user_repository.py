"""Repositorio de acceso a datos para la entidad Usuario (usuarios y roles)."""

from typing import Any, List, Optional
from src.domain.models import Role, User
from src.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """Operaciones de persistencia para la gestión y autenticación de usuarios."""

    @staticmethod
    def _map_row_to_user(row: dict) -> User:
        """Mapea una fila de base de datos a un objeto de dominio User."""
        return User(
            id_usuario=row["id_usuario"],
            id_rol=row["id_rol"],
            username=row["username"],
            password_hash=row["password_hash"],
            nombre_completo=row["nombre_completo"],
            email=row["email"],
            activo=row["activo"],
            fecha_creacion=row.get("fecha_creacion"),
            rol_nombre=row.get("rol_nombre"),
        )

    @staticmethod
    def _map_row_to_role(row: dict) -> Role:
        """Mapea una fila de la tabla roles a un objeto de dominio Role."""
        return Role(
            id_rol=row["id_rol"],
            nombre=row["nombre"],
            descripcion=row.get("descripcion", ""),
        )

    def get_by_username(self, username: str) -> Optional[User]:
        """Obtiene un usuario por su nombre de usuario, incluyendo el nombre de su rol."""
        query = """
            SELECT 
                u.id_usuario,
                u.id_rol,
                u.username,
                u.password_hash,
                u.nombre_completo,
                u.email,
                u.activo,
                u.fecha_creacion,
                r.nombre AS rol_nombre
            FROM usuarios u
            INNER JOIN roles r ON u.id_rol = r.id_rol
            WHERE LOWER(u.username) = LOWER(%s);
        """
        row = self.execute_query_one(query, (username.strip(),))
        return self._map_row_to_user(row) if row else None

    def get_by_id(self, id_usuario: int) -> Optional[User]:
        """Obtiene un usuario por su ID primario."""
        query = """
            SELECT 
                u.id_usuario,
                u.id_rol,
                u.username,
                u.password_hash,
                u.nombre_completo,
                u.email,
                u.activo,
                u.fecha_creacion,
                r.nombre AS rol_nombre
            FROM usuarios u
            INNER JOIN roles r ON u.id_rol = r.id_rol
            WHERE u.id_usuario = %s;
        """
        row = self.execute_query_one(query, (id_usuario,))
        return self._map_row_to_user(row) if row else None

    def get_by_email(self, email: str) -> Optional[User]:
        """Obtiene un usuario por su dirección de correo electrónico."""
        query = """
            SELECT 
                u.id_usuario,
                u.id_rol,
                u.username,
                u.password_hash,
                u.nombre_completo,
                u.email,
                u.activo,
                u.fecha_creacion,
                r.nombre AS rol_nombre
            FROM usuarios u
            INNER JOIN roles r ON u.id_rol = r.id_rol
            WHERE LOWER(u.email) = LOWER(%s);
        """
        row = self.execute_query_one(query, (email.strip(),))
        return self._map_row_to_user(row) if row else None

    def list_all(
        self,
        search: Optional[str] = None,
        id_rol: Optional[int] = None,
        activo: Optional[bool] = None,
    ) -> List[User]:
        """Lista usuarios con soporte para filtrado dinámico por texto, rol y estado activo."""
        query = """
            SELECT 
                u.id_usuario,
                u.id_rol,
                u.username,
                u.password_hash,
                u.nombre_completo,
                u.email,
                u.activo,
                u.fecha_creacion,
                r.nombre AS rol_nombre
            FROM usuarios u
            INNER JOIN roles r ON u.id_rol = r.id_rol
            WHERE 1=1
        """
        params: list[Any] = []

        if search:
            query += """
                AND (
                    u.username ILIKE %s 
                    OR u.nombre_completo ILIKE %s 
                    OR u.email ILIKE %s
                )
            """
            pattern = f"%{search.strip()}%"
            params.extend([pattern, pattern, pattern])

        if id_rol is not None:
            query += " AND u.id_rol = %s"
            params.append(id_rol)

        if activo is not None:
            query += " AND u.activo = %s"
            params.append(activo)

        query += " ORDER BY u.id_usuario ASC;"
        rows = self.execute_query(query, tuple(params) if params else None)
        return [self._map_row_to_user(r) for r in rows]

    def create(self, user: User, conn: Any = None) -> User:
        """Inserta un nuevo usuario en la base de datos y retorna la entidad con ID asignado."""
        query = """
            INSERT INTO usuarios (
                id_rol, username, password_hash, nombre_completo, email, activo
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id_usuario, id_rol, username, password_hash, nombre_completo, email, activo, fecha_creacion;
        """
        params = (
            user.id_rol,
            user.username.strip(),
            user.password_hash,
            user.nombre_completo.strip(),
            user.email.strip().lower(),
            user.activo,
        )
        row = self.execute_query_one(query, params, conn=conn)
        if not row:
            raise RuntimeError("Fallo al crear usuario: No se retornaron datos tras el INSERT.")

        # Obtener el nombre del rol asignado
        role = self.get_role_by_id(row["id_rol"])
        user_created = self._map_row_to_user(row)
        user_created.rol_nombre = role.nombre if role else ""
        return user_created

    def update(self, user: User, conn: Any = None) -> User:
        """Actualiza los datos personales, rol y estado activo de un usuario existente."""
        query = """
            UPDATE usuarios
            SET 
                nombre_completo = %s,
                email = %s,
                id_rol = %s,
                activo = %s
            WHERE id_usuario = %s
            RETURNING id_usuario, id_rol, username, password_hash, nombre_completo, email, activo, fecha_creacion;
        """
        params = (
            user.nombre_completo.strip(),
            user.email.strip().lower(),
            user.id_rol,
            user.activo,
            user.id_usuario,
        )
        row = self.execute_query_one(query, params, conn=conn)
        if not row:
            raise RuntimeError(f"Fallo al actualizar usuario ID {user.id_usuario}: Registro no encontrado.")

        role = self.get_role_by_id(row["id_rol"])
        user_updated = self._map_row_to_user(row)
        user_updated.rol_nombre = role.nombre if role else ""
        return user_updated

    def update_password_hash(self, id_usuario: int, password_hash: str, conn: Any = None) -> bool:
        """Actualiza el hash de la contraseña de un usuario."""
        query = "UPDATE usuarios SET password_hash = %s WHERE id_usuario = %s;"
        affected = self.execute_non_query(query, (password_hash, id_usuario), conn=conn)
        return affected > 0

    def set_active_status(self, id_usuario: int, activo: bool, conn: Any = None) -> bool:
        """Habilita o deshabilita la cuenta de acceso de un usuario."""
        query = "UPDATE usuarios SET activo = %s WHERE id_usuario = %s;"
        affected = self.execute_non_query(query, (activo, id_usuario), conn=conn)
        return affected > 0

    def delete(self, id_usuario: int, conn: Any = None) -> bool:
        """Elimina físicamente un usuario si no posee referencias foráneas."""
        query = "DELETE FROM usuarios WHERE id_usuario = %s;"
        affected = self.execute_non_query(query, (id_usuario,), conn=conn)
        return affected > 0

    def has_operational_records(self, id_usuario: int) -> bool:
        """Comprueba si el usuario tiene registros vinculados en contratos, reservas, mantenimientos o devoluciones."""
        queries = [
            "SELECT 1 FROM contratos WHERE id_usuario = %s LIMIT 1;",
            "SELECT 1 FROM reservas WHERE id_usuario = %s LIMIT 1;",
            "SELECT 1 FROM devoluciones WHERE id_usuario = %s LIMIT 1;",
            "SELECT 1 FROM mantenimientos WHERE id_usuario = %s LIMIT 1;",
            "SELECT 1 FROM liquidaciones WHERE id_usuario = %s LIMIT 1;",
            "SELECT 1 FROM pagos WHERE id_usuario = %s LIMIT 1;",
        ]
        for q in queries:
            if self.execute_query_one(q, (id_usuario,)):
                return True
        return False

    def list_roles(self) -> List[Role]:
        """Retorna todos los roles disponibles en el sistema."""
        query = "SELECT id_rol, nombre, descripcion FROM roles ORDER BY id_rol ASC;"
        rows = self.execute_query(query)
        return [self._map_row_to_role(r) for r in rows]

    def get_role_by_id(self, id_rol: int) -> Optional[Role]:
        """Obtiene un rol por su identificador primario."""
        query = "SELECT id_rol, nombre, descripcion FROM roles WHERE id_rol = %s;"
        row = self.execute_query_one(query, (id_rol,))
        return self._map_row_to_role(row) if row else None

    def get_role_by_name(self, nombre: str) -> Optional[Role]:
        """Obtiene un rol por su nombre."""
        query = "SELECT id_rol, nombre, descripcion FROM roles WHERE LOWER(nombre) = LOWER(%s);"
        row = self.execute_query_one(query, (nombre.strip(),))
        return self._map_row_to_role(row) if row else None

    def count_users_kpis(self) -> dict[str, int]:
        """Retorna indicadores agregados para las tarjetas de métricas del módulo."""
        query = """
            SELECT 
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE activo = TRUE) AS activos,
                COUNT(*) FILTER (WHERE activo = FALSE) AS inactivos
            FROM usuarios;
        """
        row = self.execute_query_one(query) or {"total": 0, "activos": 0, "inactivos": 0}
        roles_count = self.execute_scalar("SELECT COUNT(*) FROM roles;") or 0
        return {
            "total": int(row["total"]),
            "activos": int(row["activos"]),
            "inactivos": int(row["inactivos"]),
            "roles": int(roles_count),
        }
