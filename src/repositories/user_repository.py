"""Repositorio de acceso a datos para la entidad Usuario (usuarios y roles)."""

from typing import List, Optional
from src.domain.models import User
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

    def get_by_username(self, username: str) -> Optional[User]:
        """Obtiene un usuario por su nombre de usuario, incluyendo el nombre de su rol.

        Args:
            username: Nombre de usuario a buscar.

        Returns:
            Instancia de User si existe, o None si no se encuentra.
        """
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
            WHERE u.username = %s;
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

    def list_all(self) -> List[User]:
        """Lista todos los usuarios registrados en el sistema."""
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
            ORDER BY u.id_usuario ASC;
        """
        rows = self.execute_query(query)
        return [self._map_row_to_user(r) for r in rows]
