"""Módulo de gestión de conexiones y pool para PostgreSQL.

Soporta psycopg2 (ThreadedConnectionPool) y psycopg 3 (ConnectionPool)
con cursores de diccionario y context managers para transacciones seguras.
"""

from contextlib import contextmanager
from typing import Any, Generator, Optional
import threading

from src.config.settings import get_settings
from src.core.exceptions import DatabaseConnectionError
from src.core.logger import get_logger

logger = get_logger(__name__)

# Detección automática del controlador disponible
DRIVER_NAME: Optional[str] = None

try:
    import psycopg2
    from psycopg2 import pool as psycopg2_pool
    from psycopg2.extras import RealDictCursor
    DRIVER_NAME = "psycopg2"
except ImportError:
    try:
        import psycopg
        from psycopg import rows as psycopg_rows
        from psycopg_pool import ConnectionPool as Psycopg3Pool
        DRIVER_NAME = "psycopg"
    except ImportError:
        DRIVER_NAME = None


class DatabaseManager:
    """Administrador de pool de conexiones para PostgreSQL con soporte para hilos (Thread-safe)."""

    _instance: Optional["DatabaseManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "DatabaseManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self.settings = get_settings().database
        self._pool: Any = None
        self._driver: Optional[str] = DRIVER_NAME
        self._is_connected = False
        self._initialized = True

    @property
    def driver(self) -> Optional[str]:
        return self._driver

    def initialize_pool(self) -> None:
        """Inicializa el pool de conexiones según el driver disponible."""
        if self._is_connected and self._pool is not None:
            return

        if self._driver is None:
            raise DatabaseConnectionError(
                message="No se encontró ningún controlador PostgreSQL instalado ('psycopg2-binary' o 'psycopg'). "
                        "Por favor instálalo ejecutando: pip install psycopg2-binary o pip install psycopg[binary,pool]",
                code="NO_DB_DRIVER_INSTALLED",
            )

        try:
            if self._driver == "psycopg2":
                logger.info(
                    "Inicializando ThreadedConnectionPool (psycopg2) hacia %s:%s/%s (min=%s, max=%s)",
                    self.settings.host,
                    self.settings.port,
                    self.settings.name,
                    self.settings.pool_min,
                    self.settings.pool_max,
                )
                self._pool = psycopg2_pool.ThreadedConnectionPool(
                    minconn=self.settings.pool_min,
                    maxconn=self.settings.pool_max,
                    **self.settings.dsn_dict,
                )
            elif self._driver == "psycopg":
                logger.info(
                    "Inicializando ConnectionPool (psycopg 3) hacia %s:%s/%s",
                    self.settings.host,
                    self.settings.port,
                    self.settings.name,
                )
                conninfo = self.settings.connection_uri
                self._pool = Psycopg3Pool(
                    conninfo=conninfo,
                    min_size=self.settings.pool_min,
                    max_size=self.settings.pool_max,
                    timeout=self.settings.timeout,
                    open=True,
                )

            self._is_connected = True
            logger.info("Pool de conexiones inicializado satisfactoriamente.")

        except Exception as e:
            self._is_connected = False
            error_msg = f"No se pudo conectar al servidor PostgreSQL en {self.settings.host}:{self.settings.port}: {e}"
            logger.error(error_msg)
            raise DatabaseConnectionError(message=error_msg, details=str(e)) from e

    def test_connection(self) -> tuple[bool, str]:
        """Verifica la conectividad real con la base de datos ejecutando una consulta simple."""
        try:
            self.initialize_pool()
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 AS status, current_database() AS db_name, version() AS db_version;")
                    row = cur.fetchone()
                    logger.info("Prueba de conexión exitosa: %s", row)
                    return True, f"Conexión exitosa a la base de datos '{self.settings.name}'."
        except Exception as e:
            logger.warning("Fallo en prueba de conexión: %s", e)
            return False, str(e)

    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        """Context manager para obtener una conexión del pool y retornarla al finalizar."""
        if not self._is_connected or self._pool is None:
            self.initialize_pool()

        conn = None
        try:
            if self._driver == "psycopg2":
                conn = self._pool.getconn()
            elif self._driver == "psycopg":
                conn = self._pool.getconn()

            yield conn

        finally:
            if conn is not None and self._pool is not None:
                if self._driver == "psycopg2":
                    self._pool.putconn(conn)
                elif self._driver == "psycopg":
                    self._pool.putconn(conn)

    @contextmanager
    def transaction(self) -> Generator[Any, None, None]:
        """Context manager que maneja una transacción ACID atómica (COMMIT / ROLLBACK)."""
        with self.get_connection() as conn:
            try:
                if self._driver == "psycopg2":
                    conn.autocommit = False
                yield conn
                conn.commit()
            except Exception as e:
                if conn is not None:
                    try:
                        conn.rollback()
                        logger.warning("Transacción revertida (ROLLBACK) debido a: %s", e)
                    except Exception as rollback_err:
                        logger.error("Error al ejecutar ROLLBACK: %s", rollback_err)
                raise

    @contextmanager
    def cursor(self, conn: Any = None, dict_cursor: bool = True) -> Generator[Any, None, None]:
        """Retorna un cursor (por defecto mapeado a diccionario RealDictCursor) cerrado al terminar."""
        if conn is not None:
            # Reutiliza conexión externa (ej: dentro de una transacción)
            if self._driver == "psycopg2":
                cur_factory = RealDictCursor if dict_cursor else None
                cur = conn.cursor(cursor_factory=cur_factory)
            else:
                row_factory = psycopg_rows.dict_row if dict_cursor else None
                cur = conn.cursor(row_factory=row_factory)

            try:
                yield cur
            finally:
                cur.close()
        else:
            # Obtiene conexión temporal del pool
            with self.get_connection() as borrowed_conn:
                if self._driver == "psycopg2":
                    cur_factory = RealDictCursor if dict_cursor else None
                    cur = borrowed_conn.cursor(cursor_factory=cur_factory)
                else:
                    row_factory = psycopg_rows.dict_row if dict_cursor else None
                    cur = borrowed_conn.cursor(row_factory=row_factory)

                try:
                    yield cur
                finally:
                    cur.close()

    def close_pool(self) -> None:
        """Cierra todas las conexiones del pool al apagar la aplicación."""
        with self._lock:
            if self._pool is not None:
                logger.info("Cerrando el pool de conexiones de base de datos...")
                try:
                    self._pool.closeall() if hasattr(self._pool, "closeall") else self._pool.close()
                except Exception as e:
                    logger.warning("Excepción al cerrar el pool: %s", e)
                finally:
                    self._pool = None
                    self._is_connected = False
                    logger.info("Pool de conexiones cerrado correctamente.")


# Instancia global reutilizable
db_manager = DatabaseManager()
