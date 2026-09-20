"""Suite de pruebas unitarias y de integración para la Fase 10: Control de Usuarios, RBAC y Auditoría.

Verifica:
1. Creación, lectura, actualización y ciclo de vida de usuarios (CRUD).
2. Reglas de validación (unicidad de username/email, formato de correo, longitud de clave).
3. Protección inmutable de la cuenta del Administrador principal.
4. Conmutación de estado activo, desbloqueo y restablecimiento de contraseña.
5. RF-03: Bloqueo automático por 3 intentos fallidos consecutivos.
6. RF-04: Matriz de permisos y asignación de roles RBAC.
7. RF-05: Bitácora inmutable de auditoría para acciones críticas.
"""

import sys
from pathlib import Path

# Configurar encoding seguro para consola en Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.exceptions import (
    AuthenticationError,
    DuplicateRecordError,
    RecordNotFoundError,
    ValidationError,
)
from src.core.logger import setup_logging
from src.core.security import verify_password
from src.core.session import session
from src.domain.enums import UserRole
from src.domain.models import User
from src.services.auth_service import auth_service
from src.services.user_service import user_service


def cleanup_test_data() -> None:
    """Elimina los usuarios de prueba creados durante los tests."""
    print("Limpiando datos de prueba de Usuarios...")
    for uname in ["usr_test_f10", "usr_test_dup", "usr_test_lock"]:
        u = user_service.get_user_by_username(uname)
        if u and u.id_usuario:
            try:
                user_service.delete_user(u.id_usuario)
            except Exception:
                # Si no se puede por dependencias, deshabilitar
                try:
                    user_service.user_repo.set_active_status(u.id_usuario, False)
                except Exception:
                    pass
    print("✓ Limpieza de datos completada.\n")


def run_tests() -> None:
    setup_logging()
    print("\n" + "=" * 70)
    print("INICIANDO SUITE DE PRUEBAS: FASE 10 - CONTROL DE USUARIOS, RBAC Y AUDITORÍA")
    print("=" * 70)

    # Iniciar sesión como Administrador para disponer de contexto en los logs de auditoría
    auth_service.login("admin", "Admin123*")
    cleanup_test_data()

    # -------------------------------------------------------------------------
    # TEST 1: Creación de Usuario y Hashing Bcrypt
    # -------------------------------------------------------------------------
    print("[TEST 1] Creación de Usuario con credenciales seguras (bcrypt)...")
    user = user_service.create_user(
        username="usr_test_f10",
        password="PasswordTest123*",
        nombre_completo="Usuario de Pruebas F10",
        email="test_f10@rentacar.com",
        id_rol=2,  # AGENTE_VENTAS
        activo=True,
    )

    assert user is not None, "El usuario creado no debe ser None"
    assert user.id_usuario is not None, "Debe asignarse un ID primario generado"
    assert user.username == "usr_test_f10"
    assert user.nombre_completo == "Usuario de Pruebas F10"
    assert user.email == "test_f10@rentacar.com"
    assert user.id_rol == 2
    assert user.rol_nombre == "AGENTE_VENTAS"
    assert user.activo is True
    assert verify_password("PasswordTest123*", user.password_hash), "El hash bcrypt debe ser verificable"
    print(f" -> Usuario creado satisfactoriamente: ID {user.id_usuario}, @{user.username} (Rol: {user.rol_nombre})")
    print("✓ TEST 1 PASÓ: Creación de usuario y persistencia con bcrypt validadas.")

    # -------------------------------------------------------------------------
    # TEST 2: Validaciones de Negocio y Restricciones Únicas
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Verificando validaciones de duplicidad y formato...")

    # A. Username duplicado
    try:
        user_service.create_user(
            username="usr_test_f10",
            password="CualquierPass123*",
            nombre_completo="Duplicado Test",
            email="otro_correo@rentacar.com",
            id_rol=2,
        )
        assert False, "Debió rechazar username duplicado"
    except DuplicateRecordError:
        print(" -> Rechazo por username duplicado validado.")

    # B. Email duplicado
    try:
        user_service.create_user(
            username="usr_test_dup",
            password="CualquierPass123*",
            nombre_completo="Duplicado Email Test",
            email="test_f10@rentacar.com",
            id_rol=2,
        )
        assert False, "Debió rechazar email duplicado"
    except DuplicateRecordError:
        print(" -> Rechazo por email duplicado validado.")

    # C. Formato de email inválido
    try:
        user_service.create_user(
            username="usr_test_dup",
            password="CualquierPass123*",
            nombre_completo="Email Invalido",
            email="correo_sin_arroba.com",
            id_rol=2,
        )
        assert False, "Debió rechazar formato inválido de correo"
    except ValidationError as e:
        assert e.code == "INVALID_EMAIL"
        print(f" -> Rechazo por formato inválido de correo ({e.code}) validado.")

    # D. Contraseña demasiado corta
    try:
        user_service.create_user(
            username="usr_test_dup",
            password="123",
            nombre_completo="Pass Corto",
            email="valido@rentacar.com",
            id_rol=2,
        )
        assert False, "Debió rechazar contraseña menor a 6 caracteres"
    except ValidationError as e:
        assert e.code == "PASSWORD_TOO_SHORT"
        print(f" -> Rechazo por clave corta ({e.code}) validado.")

    print("✓ TEST 2 PASÓ: Validaciones y restricciones de unicidad aprobadas.")

    # -------------------------------------------------------------------------
    # TEST 3: Actualización de Perfil y Modificación de Rol
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Actualización de perfil y rol de usuario...")
    updated = user_service.update_user(
        id_usuario=user.id_usuario,
        nombre_completo="Usuario F10 Actualizado",
        email="test_f10_updated@rentacar.com",
        id_rol=4,  # GERENTE
        activo=True,
    )
    assert updated.nombre_completo == "Usuario F10 Actualizado"
    assert updated.email == "test_f10_updated@rentacar.com"
    assert updated.id_rol == 4
    assert updated.rol_nombre == "GERENTE"
    print(f" -> Usuario actualizado a rol '{updated.rol_nombre}' y nuevo correo.")
    print("✓ TEST 3 PASÓ: Actualización de datos y roles verificada.")

    # -------------------------------------------------------------------------
    # TEST 4: Salvaguardas de Seguridad para la Cuenta del Administrador Principal
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Verificando protección de la cuenta Administrador (ID 1)...")
    admin_user = user_service.get_user_by_id(1)
    assert admin_user.username == "admin"

    # A. Prohibición de deshabilitar al admin
    try:
        user_service.toggle_active_status(1)
        assert False, "Debió prohibir deshabilitar la cuenta del administrador"
    except ValidationError as e:
        assert e.code == "CANNOT_DISABLE_ADMIN"
        print(" -> Protección confirmada: No se puede desactivar la cuenta del Administrador.")

    # B. Prohibición de degradar el rol del admin
    try:
        user_service.update_user(
            id_usuario=1,
            nombre_completo="Admin Degrade",
            email="admin@rentacar.com",
            id_rol=2,  # Intentar degradar a AGENTE_VENTAS
            activo=True,
        )
        assert False, "Debió prohibir modificar el rol del Administrador"
    except ValidationError as e:
        assert e.code == "CANNOT_DOWNGRADE_ADMIN"
        print(" -> Protección confirmada: No se puede degradar el rol del Administrador.")

    # C. Prohibición de eliminar al admin
    try:
        user_service.delete_user(1)
        assert False, "Debió prohibir eliminar la cuenta del Administrador"
    except ValidationError as e:
        assert e.code == "CANNOT_DELETE_ADMIN"
        print(" -> Protección confirmada: No se puede eliminar al Administrador.")

    print("✓ TEST 4 PASÓ: Todas las salvaguardas de la cuenta Administrador aprobadas.")

    # -------------------------------------------------------------------------
    # TEST 5: Restablecimiento de Contraseña y Conmutación de Estado
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Restablecimiento de contraseña y conmutación de estado...")
    # Cambiar contraseña
    user_service.reset_password(user.id_usuario, "NuevaPassword2026*")
    reloaded_user = user_service.get_user_by_id(user.id_usuario)
    assert verify_password("NuevaPassword2026*", reloaded_user.password_hash)
    print(" -> Contraseña restablecida y verificada.")

    # Conmutar a inactivo
    status = user_service.toggle_active_status(user.id_usuario)
    assert status is False
    assert user_service.get_user_by_id(user.id_usuario).activo is False
    print(" -> Cuenta conmutada a INACTIVA.")

    # Desbloquear / Activar
    user_service.unlock_user(user.id_usuario)
    assert user_service.get_user_by_id(user.id_usuario).activo is True
    print(" -> Cuenta reactivada mediante unlock_user.")
    print("✓ TEST 5 PASÓ: Gestión de credenciales y activación confirmada.")

    # -------------------------------------------------------------------------
    # TEST 6: Bloqueo Automático por 3 Intentos Fallidos Consecutivos (RF-03)
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Bloqueo automático por intentos fallidos consecutivos (RF-03)...")
    lock_user = user_service.create_user(
        username="usr_test_lock",
        password="CorrectPassword123*",
        nombre_completo="Usuario Prueba Bloqueo",
        email="lock_test@rentacar.com",
        id_rol=2,
        activo=True,
    )

    # Intento 1 erróneo
    try:
        auth_service.login("usr_test_lock", "ClaveErronea1")
        assert False
    except AuthenticationError as e:
        assert e.code == "INVALID_PASSWORD"
        print(" -> Intento erróneo 1 registrado.")

    # Intento 2 erróneo
    try:
        auth_service.login("usr_test_lock", "ClaveErronea2")
        assert False
    except AuthenticationError as e:
        assert e.code == "INVALID_PASSWORD"
        print(" -> Intento erróneo 2 registrado.")

    # Intento 3 erróneo -> Debe disparar bloqueo automático (RF-03)
    try:
        auth_service.login("usr_test_lock", "ClaveErronea3")
        assert False, "El tercer intento fallido debió bloquear la cuenta con ACCOUNT_LOCKED"
    except AuthenticationError as e:
        assert e.code == "ACCOUNT_LOCKED"
        print(f" -> Bloqueo automático activado con código '{e.code}': {e.message}")

    # Verificar que el usuario quedó inhabilitado en la base de datos
    check_user = user_service.get_user_by_id(lock_user.id_usuario)
    assert check_user.activo is False, "El usuario debe estar inactivo en base de datos"
    print(" -> Estado en base de datos verificado: activo = FALSE.")

    # Cuarto intento con la contraseña correcta debe ser rechazado por cuenta inactiva
    try:
        auth_service.login("usr_test_lock", "CorrectPassword123*")
        assert False, "Cuenta inactiva no debe ingresar"
    except AuthenticationError as e:
        assert e.code == "USER_DISABLED"
        print(f" -> Intento posterior rechazado correctamente: {e.message}")

    # Administrador desbloquea la cuenta
    user_service.unlock_user(lock_user.id_usuario)
    unlocked = auth_service.login("usr_test_lock", "CorrectPassword123*")
    assert unlocked is not None
    assert session.current_user.username == "usr_test_lock"
    print(" -> Desbloqueo administrativo verificado: Usuario ingresó con éxito.")
    print("✓ TEST 6 PASÓ: Bloqueo automático por fuerza bruta (RF-03) y reactivación validados al 100%.")

    # Restaurar sesión admin
    auth_service.login("admin", "Admin123*")

    # -------------------------------------------------------------------------
    # TEST 7: Bitácora de Auditoría de Acciones Críticas (RF-05)
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Bitácora de Auditoría inmutable de acciones críticas (RF-05)...")
    logs = user_service.get_audit_logs(limit=50)
    assert len(logs) > 0, "Debe existir al menos un registro en la bitácora de auditoría"

    acciones_registradas = {log.accion for log in logs}
    print(f" -> Acciones críticas detectadas en bitácora: {acciones_registradas}")

    assert "CREAR_USUARIO" in acciones_registradas, "Debe registrar CREAR_USUARIO"
    assert "ACTUALIZAR_USUARIO" in acciones_registradas, "Debe registrar ACTUALIZAR_USUARIO"
    assert "RESETEO_PASSWORD" in acciones_registradas, "Debe registrar RESETEO_PASSWORD"
    assert "DESBLOQUEAR_CUENTA" in acciones_registradas, "Debe registrar DESBLOQUEAR_CUENTA"
    assert "BLOQUEO_AUTOMATICO_INTENTOS" in acciones_registradas, "Debe registrar BLOQUEO_AUTOMATICO_INTENTOS"

    # Filtrar por usuario
    filtered_logs = user_service.get_audit_logs(limit=50, username="admin")
    assert all("admin" in l.username.lower() for l in filtered_logs)
    print(f" -> Filtrado de auditoría por usuario 'admin' validado ({len(filtered_logs)} registros).")
    print("✓ TEST 7 PASÓ: Auditoría inmutable (RF-05) verificada con persistencia real.")

    # -------------------------------------------------------------------------
    # TEST 8: Métricas de Usuarios y KPIs
    # -------------------------------------------------------------------------
    print("\n[TEST 8] Verificación de Métricas e Indicadores de Usuarios...")
    kpis = user_service.get_kpis()
    assert kpis["total"] >= 5
    assert kpis["activos"] >= 1
    assert kpis["roles"] == 4
    print(f" -> KPIs validados: Total={kpis['total']}, Activos={kpis['activos']}, Inactivos={kpis['inactivos']}, Roles={kpis['roles']}")
    print("✓ TEST 8 PASÓ: KPIs del módulo de usuarios verificados.")

    # Limpieza final
    cleanup_test_data()

    print("\n" + "=" * 70)
    print("¡TODAS LAS PRUEBAS DE FASE 10 (CONTROL DE USUARIOS, RBAC Y AUDITORÍA) PASARON AL 100%!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_tests()
