"""Punto de entrada principal (Entry Point) de la aplicación de escritorio.

Orquesta el ciclo de vida de autenticación:
Inicia en LoginView -> Tras login exitoso -> Abre DashboardView -> Tras logout -> Regresa a LoginView.
"""

import sys
from typing import Optional
from PySide6.QtWidgets import QApplication

from src.config.settings import get_settings
from src.core.logger import get_logger, setup_logging
from src.database.connection import db_manager
from src.domain.models import User
from src.ui.views.login_view import LoginView
from src.ui.views.dashboard_view import DashboardView


class AppCoordinator:
    """Coordina las transiciones desacopladas entre Login y Dashboard."""

    def __init__(self) -> None:
        self.login_view = LoginView()
        self.dashboard_view: Optional[DashboardView] = None

        # Conectar señal de login exitoso
        self.login_view.login_success.connect(self._on_login_success)

    def start(self) -> None:
        """Inicia el flujo presentando la ventana de Login."""
        self.login_view.show()

    def _on_login_success(self, user: User) -> None:
        """Cierra el Login y abre el Dashboard con la sesión del usuario."""
        self.login_view.hide()
        self.dashboard_view = DashboardView()
        self.dashboard_view.logout_requested.connect(self._on_logout)
        self.dashboard_view.show()

    def _on_logout(self) -> None:
        """Cierra el Dashboard y reabre el Login con campos limpios."""
        if self.dashboard_view:
            self.dashboard_view.close()
            self.dashboard_view = None

        self.login_view.clear_inputs()
        self.login_view.show()


def main() -> int:
    """Función de arranque e inicialización de la aplicación."""
    # 1. Configuración de logging inicial
    setup_logging()
    logger = get_logger("main")
    settings = get_settings()

    logger.info("====================================================================")
    logger.info("Iniciando %s", settings.app.name)
    logger.info("Entorno: %s | Modo Debug: %s", settings.app.env, settings.app.debug)
    logger.info("Controlador de base de datos detectado: %s", db_manager.driver)
    logger.info("Versión de Python: %s", sys.version.split()[0])
    logger.info("====================================================================")

    # 2. Inicializar aplicación Qt
    app = QApplication(sys.argv)
    app.setApplicationName(settings.app.name)
    app.setOrganizationName("UNAN")

    # Registro de cierre seguro del pool de conexiones al terminar la aplicación
    app.aboutToQuit.connect(db_manager.close_pool)

    # 3. Arrancar el coordinador de pantallas
    coordinator = AppCoordinator()
    coordinator.start()

    # 4. Bucle principal de eventos
    exit_code = app.exec()
    logger.info("Aplicación finalizada con código de salida: %s", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
