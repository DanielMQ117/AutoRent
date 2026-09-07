"""Configuración centralizada de la aplicación y carga de variables de entorno."""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Ruta raíz del proyecto (agencia_de_autos/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Cargar variables de entorno desde el archivo .env en la raíz
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)


@dataclass(frozen=True)
class DatabaseSettings:
    """Configuración de persistencia para PostgreSQL."""
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    name: str = os.getenv("DB_NAME", "agencia_autos_db")
    user: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "postgres")
    pool_min: int = int(os.getenv("DB_POOL_MIN", "1"))
    pool_max: int = int(os.getenv("DB_POOL_MAX", "10"))
    timeout: int = int(os.getenv("DB_TIMEOUT", "30"))

    @property
    def connection_uri(self) -> str:
        """Retorna la cadena de conexión estándar en formato URI."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def dsn_dict(self) -> dict:
        """Retorna un diccionario de parámetros compatible con psycopg/psycopg2."""
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.name,
            "user": self.user,
            "password": self.password,
            "connect_timeout": self.timeout,
        }


@dataclass(frozen=True)
class LoggingSettings:
    """Configuración del sistema de logs."""
    level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_dir: Path = BASE_DIR / os.getenv("LOG_DIR", "logs")
    log_file: str = os.getenv("LOG_FILE", "app.log")

    @property
    def log_path(self) -> Path:
        """Ruta absoluta al archivo de log principal."""
        return self.log_dir / self.log_file


@dataclass(frozen=True)
class AppSettings:
    """Configuración general de la aplicación."""
    name: str = os.getenv("APP_NAME", "AutoRent Pro - Sistema de Alquiler de Automóviles")
    env: str = os.getenv("APP_ENV", "development")
    debug: bool = os.getenv("APP_DEBUG", "true").lower() in ("true", "1", "yes")
    base_dir: Path = BASE_DIR


class Settings:
    """Contenedor singleton de la configuración global del sistema."""

    def __init__(self) -> None:
        self.app = AppSettings()
        self.database = DatabaseSettings()
        self.logging = LoggingSettings()

        # Asegurar existencia del directorio de logs
        self.logging.log_dir.mkdir(parents=True, exist_ok=True)


# Instancia única reutilizable
_settings_instance: Settings | None = None


def get_settings() -> Settings:
    """Retorna la instancia singleton de la configuración del sistema."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
