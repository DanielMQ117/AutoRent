"""Punto de entrada principal (Entry Point) de la aplicación de escritorio.

Inicializa la configuración, el sistema de logging, el ciclo de eventos de PySide6
y gestiona el cierre seguro del pool de conexiones a la base de datos.
"""

import sys
from PySide6.QtWidgets import QApplication

from src.config.settings import get_settings
from src.core.logger import get_logger, setup_logging
from src.database.connection import db_manager
from src.ui.main_window import MainWindow


def main() -> int:
    """Función de arranque e inicialización del sistema."""
    # 1. Configurar logging inicial
    setup_logging()
    logger = get_logger("main")
    settings = get_settings()

    logger.info("====================================================================")
    logger.info("Iniciando %s", settings.app.name)
    logger.info("Entorno: %s | Modo Debug: %s", settings.app.env, settings.app.debug)
    logger.info("Controlador de base de datos detectado: %s", db_manager.driver)
    logger.info("Versión de Python: %s", sys.version.split()[0])
    logger.info("====================================================================")

    # 2. Inicializar ciclo de eventos de PySide6
    app = QApplication(sys.argv)
    app.setApplicationName(settings.app.name)
    app.setOrganizationName("UNAN")

    # Registrar el cierre seguro del pool de conexiones al salir
    app.aboutToQuit.connect(db_manager.close_pool)

    # 3. Instanciar y presentar la ventana principal
    window = MainWindow()
    window.show()

    # 4. Iniciar bucle de eventos
    exit_code = app.exec()
    logger.info("Aplicación finalizada con código de salida: %s", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
