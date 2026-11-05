"""Dependencias de seguridad, autenticación JWT y contexto Multi-Tenant (RLS) para FastAPI.

Sincroniza en cada petición HTTP:
1. La validación del token Bearer JWT (firmado con HMAC-SHA256).
2. El singleton UserSession en memoria (session.login / session.tenant_context).
3. El parámetro 'app.current_tenant_id' en PostgreSQL para las políticas Row Level Security (RLS).
"""

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Callable, Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config.settings import get_settings
from src.core.session import ROLE_MODULE_PERMISSIONS, session
from src.domain.models import User

_api_cfg = get_settings().api
JWT_SECRET_KEY = _api_cfg.jwt_secret_key
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_SECONDS = _api_cfg.jwt_expiration_seconds

security_scheme = HTTPBearer(auto_error=False)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def create_access_token(user: User, expires_in: int = JWT_EXPIRATION_SECONDS) -> str:
    """Genera un token JWT (HS256) con la identidad del usuario, rol y tenant_id de la agencia."""
    if not user.id_usuario or not user.tenant_id:
        raise ValueError("El usuario debe poseer id_usuario y tenant_id válidos para emitir un JWT.")

    now = int(time.time())
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": str(user.id_usuario),
        "id_usuario": int(user.id_usuario),
        "tenant_id": int(user.tenant_id),
        "id_rol": int(user.id_rol),
        "username": user.username,
        "nombre_completo": user.nombre_completo,
        "email": user.email,
        "rol_nombre": user.rol_nombre or "AGENTE_VENTAS",
        "agencia_nombre": user.agencia_nombre or "Agencia Activa",
        "agencia_codigo": user.agencia_codigo or f"AG-{user.tenant_id}",
        "iat": now,
        "exp": now + expires_in,
    }

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_access_token(token: str) -> dict:
    """Verifica la firma y vigencia de un token JWT HS256 y retorna su payload."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Formato de token JWT inválido.")
        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_sig = _b64url_decode(signature_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise ValueError("Firma de token JWT inválida.")

        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        exp = int(payload.get("exp", 0))
        if exp < int(time.time()):
            raise ValueError("El token JWT ha expirado.")
        if not payload.get("tenant_id"):
            raise ValueError("El token JWT carece de tenant_id (Fail-Fast).")
        return payload
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_OR_EXPIRED_TOKEN", "message": f"Token de acceso inválido o expirado: {exc}"},
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_api_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Generator[User, None, None]:
    """Dependencia FastAPI que autentica el JWT e inyecta el contexto Multi-Tenant (UserSession + PostgreSQL RLS)."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "NO_ACTIVE_TENANT",
                "message": "Autenticación requerida: No se proporcionó token Bearer con sesión de agencia activa.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    user = User(
        id_usuario=int(payload["id_usuario"]),
        tenant_id=int(payload["tenant_id"]),
        id_rol=int(payload.get("id_rol", 2)),
        username=str(payload["username"]),
        password_hash="",
        nombre_completo=str(payload.get("nombre_completo", payload["username"])),
        email=str(payload.get("email", "")),
        activo=True,
        rol_nombre=str(payload.get("rol_nombre", "AGENTE_VENTAS")),
        agencia_nombre=str(payload.get("agencia_nombre", "")),
        agencia_codigo=str(payload.get("agencia_codigo", "")),
    )

    prev_user = session.current_user
    prev_default_tid = getattr(session, "_default_tenant_id", None)
    session.login(user)
    try:
        with session.tenant_context(user.tenant_id):
            yield user
    finally:
        if prev_user is not None:
            session.login(prev_user)
        else:
            session.logout()
        session.set_default_tenant(prev_default_tid)


def require_module_permission(module_name: str) -> Callable[[User], User]:
    """Genera una dependencia RBAC que verifica que el rol del usuario en el JWT tenga permiso sobre el módulo."""
    def _checker(current_user: User = Depends(get_current_api_user)) -> User:
        role = current_user.rol_nombre or ""
        allowed = ROLE_MODULE_PERMISSIONS.get(role, set())
        if module_name.lower() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "PERMISSION_DENIED",
                    "message": f"El rol '{role}' no posee autorización para operar en el módulo '{module_name}'.",
                },
            )
        return current_user

    return _checker
