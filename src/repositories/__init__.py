"""Paquete de repositorios para acceso a datos (DAL)."""

from src.repositories.base_repository import BaseRepository
from src.repositories.user_repository import UserRepository

__all__ = ["BaseRepository", "UserRepository"]
