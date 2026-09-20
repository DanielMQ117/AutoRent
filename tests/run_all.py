"""Script ejecutor maestro de todas las suites de prueba (Fase 2 y Fase 3)."""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tests.test_auth import run_tests as run_auth_tests
from tests.test_clients import run_tests as run_clients_tests
from tests.test_vehicles import run_tests as run_vehicles_tests
from tests.test_reservations import run_tests as run_reservations_tests
from tests.test_contracts import run_tests as run_contracts_tests
from tests.test_returns import run_tests as run_returns_tests
from tests.test_maintenances import run_tests as run_maintenances_tests
from tests.test_reports import run_tests as run_reports_tests
from tests.test_users import run_tests as run_users_tests
from tests.test_ui_components import run_ui_checks


def main():
    print("\n" + "#" * 78)
    print("# EJECUTANDO SUITE COMPLETA DE PRUEBAS DE CALIDAD - AUTORENT PRO")
    print("#" * 78)

    run_auth_tests()
    run_clients_tests()
    run_vehicles_tests()
    run_reservations_tests()
    run_contracts_tests()
    run_returns_tests()
    run_maintenances_tests()
    run_reports_tests()
    run_users_tests()
    run_ui_checks()

    print("\n" + "#" * 78)
    print("# ¡TODAS LAS SUITES DE PRUEBA (AUTH, CLIENTES, FLOTA, RESERVAS, CONTRATOS, RETORNO, TALLER, REPORTES, USUARIOS, UI) PASARON! [100%]")
    print("#" * 78 + "\n")


if __name__ == "__main__":
    main()
