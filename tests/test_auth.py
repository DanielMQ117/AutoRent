"""Script automatizado de pruebas unitarias y de integración para el módulo de autenticación (Fase 2).

Verifica programáticamente:
1. Login correcto para los diferentes roles del seed.
2. Rechazo por contraseña incorrecta.
3. Rechazo por usuario inexistente.
4. Rechazo por usuario deshabilitado (activo = FALSE).
5. Control de permisos por rol (RBAC).
6. Cierre de sesión y limpieza del estado en memoria.
"""

import sys
from pathlib import Path

# Asegurar que el directorio raíz del proyecto esté en el path de búsqueda
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.exceptions import AuthenticationError, ValidationError
from src.core.logger import setup_logging
from src.core.session import session
from src.domain.enums import UserRole
from src.services.auth_service import auth_service


def run_tests() -> None:
    setup_logging()
    print("\n" + "=" * 70)
    print("EJECUTANDO SUITE DE PRUEBAS DE AUTENTICACION Y RBAC")
    print("=" * 70)

    # ------------------------------------------------------------------------
    # PRUEBA 1: LOGIN CORRECTO (ADMINISTRADOR)
    # ------------------------------------------------------------------------
    print("\n[TEST 1] Verificando login correcto para 'admin'...")
    user = auth_service.login("admin", "Admin123*")
    assert user is not None, "El usuario retornado no debe ser None"
    assert user.username == "admin"
    assert user.rol_nombre == UserRole.ADMINISTRADOR.value
    assert session.is_authenticated, "La sesión debe estar activa"
    assert session.current_user.username == "admin"
    print(" -> PASO: Login correcto y sesión establecida.")

    # ------------------------------------------------------------------------
    # PRUEBA 2: CONTRASEÑA INCORRECTA
    # ------------------------------------------------------------------------
    print("\n[TEST 2] Verificando rechazo por contraseña incorrecta...")
    try:
        auth_service.login("admin", "PasswordErronea123*")
        assert False, "Debió lanzar AuthenticationError por contraseña errónea"
    except AuthenticationError as e:
        assert e.code == "INVALID_PASSWORD"
        print(f" -> PASO: Rechazado correctamente con código '{e.code}': {e.message}")

    # ------------------------------------------------------------------------
    # PRUEBA 3: USUARIO INEXISTENTE
    # ------------------------------------------------------------------------
    print("\n[TEST 3] Verificando rechazo por usuario inexistente...")
    try:
        auth_service.login("usuario_que_no_existe", "CualquierPass123*")
        assert False, "Debió lanzar AuthenticationError por usuario no encontrado"
    except AuthenticationError as e:
        assert e.code == "USER_NOT_FOUND"
        print(f" -> PASO: Rechazado correctamente con código '{e.code}': {e.message}")

    # ------------------------------------------------------------------------
    # PRUEBA 4: USUARIO DESHABILITADO
    # ------------------------------------------------------------------------
    print("\n[TEST 4] Verificando rechazo por usuario deshabilitado (activo = FALSE)...")
    try:
        auth_service.login("inactivo", "Inactivo123*")
        assert False, "Debió lanzar AuthenticationError por usuario deshabilitado"
    except AuthenticationError as e:
        assert e.code == "USER_DISABLED"
        print(f" -> PASO: Rechazado correctamente con código '{e.code}': {e.message}")

    # ------------------------------------------------------------------------
    # PRUEBA 5: CONTROL DE PERMISOS SEGUN ROL (RBAC)
    # ------------------------------------------------------------------------
    print("\n[TEST 5] Verificando matriz de permisos RBAC para diferentes roles...")

    # A. Administrador (acceso total)
    auth_service.login("admin", "Admin123*")
    assert session.has_permission("usuarios"), "ADMIN debe tener acceso a usuarios"
    assert session.has_permission("flota"), "ADMIN debe tener acceso a flota"
    assert session.has_permission("reportes"), "ADMIN debe tener acceso a reportes"
    print(" -> Subprueba 5.1: Rol ADMINISTRADOR tiene acceso total verificado.")

    # B. Agente de Ventas (acceso a contratos, reservas, clientes; NO a usuarios ni mantenimientos)
    auth_service.login("agente1", "Agente123*")
    assert session.has_permission("contratos"), "AGENTE debe tener acceso a contratos"
    assert session.has_permission("reservas"), "AGENTE debe tener acceso a reservas"
    assert session.has_permission("clientes"), "AGENTE debe tener acceso a clientes"
    assert not session.has_permission("usuarios"), "AGENTE NO debe tener acceso a usuarios"
    assert not session.has_permission("mantenimientos"), "AGENTE NO debe tener acceso a mantenimientos"
    print(" -> Subprueba 5.2: Rol AGENTE_VENTAS tiene permisos operativos y restricciones verificadas.")

    # C. Inspector de Taller (acceso a devoluciones, mantenimientos; NO a clientes ni contratos)
    auth_service.login("taller1", "Taller123*")
    assert session.has_permission("mantenimientos"), "TALLER debe tener acceso a mantenimientos"
    assert session.has_permission("devoluciones"), "TALLER debe tener acceso a devoluciones"
    assert not session.has_permission("clientes"), "TALLER NO debe tener acceso a clientes"
    assert not session.has_permission("contratos"), "TALLER NO debe tener acceso a contratos"
    assert not session.has_permission("usuarios"), "TALLER NO debe tener acceso a usuarios"
    print(" -> Subprueba 5.3: Rol INSPECTOR_TALLER tiene permisos técnicos y restricciones verificadas.")

    # ------------------------------------------------------------------------
    # PRUEBA 6: CIERRE DE SESIÓN (LOGOUT)
    # ------------------------------------------------------------------------
    print("\n[TEST 6] Verificando cierre de sesión (Logout)...")
    assert session.is_authenticated, "La sesión debía estar activa antes del logout"
    auth_service.logout()
    assert not session.is_authenticated, "La sesión debe ser nula después del logout"
    assert session.current_user is None
    assert not session.has_permission("flota"), "Sin sesión no debe haber permisos para ningún módulo"
    print(" -> PASO: Sesión cerrada y memoria limpiada exitosamente.")

    print("\n" + "=" * 70)
    print("TODAS LAS PRUEBAS DE AUTENTICACION Y RBAC FINALIZARON CON EXITO [6/6]")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_tests()
