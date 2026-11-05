"""Configuración base de SQLAlchemy 2.0 ORM, Pool de Conexiones y Sincronización Multi-Tenant RLS."""

import os
from contextlib import contextmanager
from typing import Any, Generator, Optional
from urllib.parse import quote_plus

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from src.config.settings import get_settings
from src.core.logger import get_logger
from src.core.session import session as app_session

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Clase base declarativa de SQLAlchemy 2.0 para todos los modelos ORM del sistema."""

    pass


def build_sqlalchemy_url() -> str:
    """Construye la URL de conexión SQLAlchemy para PostgreSQL usando el driver disponible.

    Detecta automáticamente si está disponible ``psycopg2`` o ``psycopg`` (v3)
    y escapa de forma segura las credenciales desde ``DatabaseSettings``.

    Returns:
        str: Cadena DSN compatible con SQLAlchemy (ej. ``postgresql+psycopg2://...``).
    """
    db_cfg = get_settings().database
    user = quote_plus(db_cfg.user)
    password = quote_plus(db_cfg.password)
    host = db_cfg.host
    port = db_cfg.port
    name = db_cfg.name

    driver = "psycopg2"
    try:
        import psycopg2  # noqa: F401
    except ImportError:
        driver = "psycopg"

    return f"postgresql+{driver}://{user}:{password}@{host}:{port}/{name}"


def create_orm_engine() -> Engine:
    """Crea y configura la instancia global de ``Engine`` de SQLAlchemy 2.0.

    Si se detecta ejecución en entorno Serverless (``AWS_LAMBDA_FUNCTION_NAME`` o
    ``USE_NULL_POOL=true``), utiliza ``NullPool`` para evitar agotar conexiones en RDS.
    En entorno local o servidor persistente, utiliza ``QueuePool`` con ``pool_pre_ping``.

    Returns:
        Engine: Motor de base de datos SQLAlchemy configurado.
    """
    settings = get_settings()
    url = build_sqlalchemy_url()

    use_null_pool = (
        os.getenv("USE_NULL_POOL", "false").lower() in ("true", "1", "yes")
        or bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
    )

    if use_null_pool:
        logger.info("Inicializando SQLAlchemy Engine con NullPool (Modo Serverless / Lambda)")
        return create_engine(
            url,
            poolclass=NullPool,
            future=True,
        )

    logger.info(
        "Inicializando SQLAlchemy Engine con QueuePool (%s:%s/%s)",
        settings.database.host,
        settings.database.port,
        settings.database.name,
    )
    return create_engine(
        url,
        poolclass=QueuePool,
        pool_size=settings.database.pool_min,
        max_overflow=max(2, settings.database.pool_max - settings.database.pool_min),
        pool_pre_ping=True,
        future=True,
    )


# Instancia global del Engine y fábrica de sesiones ORM
engine: Engine = create_orm_engine()
SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def sync_session_rls_context(orm_session: Session) -> None:
    """Sincroniza la variable de entorno PostgreSQL ``app.current_tenant_id`` en la sesión ORM.

    Garantiza que las políticas de Row Level Security (RLS) de PostgreSQL filtren y validen
    automáticamente todas las sentencias generadas por SQLAlchemy para el inquilino activo.

    Args:
        orm_session (Session): Sesión activa de SQLAlchemy donde se inyectará el contexto RLS.
    """
    tid = app_session.active_tenant_id_or_none
    tenant_val = str(int(tid)) if tid is not None else ""
    orm_session.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, false);"),
        {"tid": tenant_val},
    )


@event.listens_for(Session, "after_begin")
def _on_session_after_begin(session: Session, transaction: Any, connection: Any) -> None:
    """Hook automático de SQLAlchemy que sincroniza el contexto RLS al iniciar cada transacción.

    Args:
        session (Session): Sesión ORM que inicia la transacción.
        transaction (Any): Transacción interna de SQLAlchemy.
        connection (Any): Conexión física subyacente de base de datos.
    """
    tid = app_session.active_tenant_id_or_none
    tenant_val = str(int(tid)) if tid is not None else ""
    connection.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, false);"),
        {"tid": tenant_val},
    )


@contextmanager
def get_orm_session(existing_session: Optional[Any] = None) -> Generator[Session, None, None]:
    """Provee un bloque de contexto transaccional seguro con una sesión de SQLAlchemy ORM.

    Si se recibe una sesión ORM externa (``existing_session`` es instancia de ``Session``),
    reutiliza dicha sesión sin cerrarla al salir del bloque para permitir transacciones
    atómicas compartidas entre múltiples repositorios. Si no se recibe (o si se recibe una
    conexión cruda legacy), abre una nueva sesión ORM sincronizada con PostgreSQL RLS,
    confirma (``commit``) al finalizar sin errores o revierte (``rollback``) ante excepciones.

    Args:
        existing_session (Optional[Any]): Sesión ORM existente opcional o ``None``.

    Yields:
        Session: Sesión activa de SQLAlchemy 2.0 lista para consultas y persistencia.
    """
    if isinstance(existing_session, Session):
        sync_session_rls_context(existing_session)
        yield existing_session
        return

    db_session: Session = SessionLocal()
    try:
        sync_session_rls_context(db_session)
        yield db_session
        db_session.commit()
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()
