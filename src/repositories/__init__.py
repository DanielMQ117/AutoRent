"""Paquete de repositorios para acceso a datos (DAL)."""

from src.repositories.base_repository import BaseRepository
from src.repositories.client_repository import ClientRepository
from src.repositories.user_repository import UserRepository
from src.repositories.vehicle_repository import VehicleRepository

__all__ = ["BaseRepository", "ClientRepository", "UserRepository", "VehicleRepository"]
