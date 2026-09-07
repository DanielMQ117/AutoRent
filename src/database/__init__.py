"""Paquete de base de datos y persistencia."""

from src.database.connection import DatabaseManager, db_manager

__all__ = ["DatabaseManager", "db_manager"]
