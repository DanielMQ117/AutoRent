"""Ventana base y marco de verificación de la arquitectura del sistema (Fase 2).

Esta vista representa exclusivamente la capa de presentación (UI).
No contiene consultas SQL ni lógica de persistencia directa.
"""

import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import get_settings
from src.core.logger import get_logger
from src.database.connection import db_manager

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """Ventana principal que verifica la integridad de la arquitectura en capas."""

    def __init__(self) -> None:
        super().__init__()
        self.settings = get_settings()
        self._init_ui()

    def _init_ui(self) -> None:
        """Inicializa los componentes visuales de la ventana principal."""
        self.setWindowTitle(self.settings.app.name)
        self.resize(850, 600)
        self.setMinimumSize(750, 500)

        # Widget central
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Layout vertical principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 30, 30, 20)
        main_layout.setSpacing(20)

        # 1. Cabecera (Header)
        header_layout = QVBoxLayout()
        title_label = QLabel(self.settings.app.name)
        title_font = QFont("Segoe UI", 18, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #1a365d;")

        subtitle_label = QLabel("Proyecto Integrador II — Ingeniería en Sistemas de Información (UNAN)")
        subtitle_label.setFont(QFont("Segoe UI", 10))
        subtitle_label.setStyleSheet("color: #718096;")

        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        main_layout.addLayout(header_layout)

        # Línea separadora
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("color: #e2e8f0;")
        main_layout.addWidget(separator)

        # 2. Panel de Arquitectura en Capas
        arch_card = QFrame()
        arch_card.setStyleSheet("""
            QFrame {
                background-color: #f7fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        arch_layout = QVBoxLayout(arch_card)
        arch_title = QLabel("Arquitectura en Capas Configurada:")
        arch_title.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        arch_title.setStyleSheet("color: #2d3748; border: none;")
        arch_layout.addWidget(arch_title)

        layers = [
            ("UI (PySide6)", "Capa de Presentación desacoplada sin consultas SQL directas."),
            ("Services (BLL)", "Capa de Lógica de Negocio, validaciones y orquestación de transacciones."),
            ("Repositories (DAL)", "Capa de Acceso a Datos con mapeo a modelos y traducción de excepciones."),
            ("PostgreSQL Database", f"Persistencia relacional en '{self.settings.database.name}' ({self.settings.database.host}:{self.settings.database.port})."),
        ]

        for layer_name, layer_desc in layers:
            row = QHBoxLayout()
            bullet = QLabel("✓")
            bullet.setStyleSheet("color: #38a169; font-weight: bold; font-size: 14px; border: none;")
            name_lbl = QLabel(f"<b>{layer_name}</b>: {layer_desc}")
            name_lbl.setStyleSheet("color: #4a5568; border: none;")
            row.addWidget(bullet)
            row.addWidget(name_lbl, stretch=1)
            arch_layout.addLayout(row)

        main_layout.addWidget(arch_card)

        # 3. Panel de Estado de Persistencia
        db_card = QFrame()
        db_card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        db_layout = QVBoxLayout(db_card)

        db_header = QHBoxLayout()
        db_title = QLabel("Estado del Conector PostgreSQL:")
        db_title.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        db_title.setStyleSheet("color: #2d3748; border: none;")

        self.status_badge = QLabel("SIN VERIFICAR")
        self.status_badge.setStyleSheet("""
            background-color: #edf2f7;
            color: #4a5568;
            padding: 4px 10px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 10px;
        """)

        db_header.addWidget(db_title)
        db_header.addStretch()
        db_header.addWidget(self.status_badge)
        db_layout.addLayout(db_header)

        self.db_details_label = QLabel("Haga clic en el botón inferior para verificar la conectividad con la base de datos.")
        self.db_details_label.setStyleSheet("color: #718096; margin-top: 5px; border: none;")
        self.db_details_label.setWordWrap(True)
        db_layout.addWidget(self.db_details_label)

        # Botón de prueba de conexión
        btn_layout = QHBoxLayout()
        self.test_btn = QPushButton("Verificar Conexión con PostgreSQL")
        self.test_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self.test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #3182ce;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
            }
            QPushButton:hover {
                background-color: #2b6cb0;
            }
            QPushButton:pressed {
                background-color: #2c5282;
            }
        """)
        self.test_btn.clicked.connect(self._handle_test_connection)
        btn_layout.addWidget(self.test_btn)
        btn_layout.addStretch()
        db_layout.addLayout(btn_layout)

        main_layout.addWidget(db_card)
        main_layout.addStretch()

        # 4. Barra de Estado (Status Bar)
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)
        status_bar.setStyleSheet("background-color: #f7fafc; color: #718096; border-top: 1px solid #e2e8f0;")
        
        driver_info = db_manager.driver or "No detectado"
        status_bar.showMessage(f"Entorno: {self.settings.app.env.upper()} | Driver: {driver_info} | Python: {sys.version.split()[0]}")

        # Realizar una prueba inicial automática
        self._handle_test_connection()

    def _handle_test_connection(self) -> None:
        """Prueba la conexión a la base de datos y actualiza los elementos visuales."""
        self.test_btn.setEnabled(False)
        self.status_badge.setText("PROBANDO...")
        self.status_badge.setStyleSheet("background-color: #feebc8; color: #c05621; padding: 4px 10px; border-radius: 4px;")
        QApplication.processEvents()

        success, message = db_manager.test_connection()

        if success:
            self.status_badge.setText("CONECTADO")
            self.status_badge.setStyleSheet("background-color: #c6f6d5; color: #22543d; padding: 4px 10px; border-radius: 4px; font-weight: bold;")
            self.db_details_label.setText(
                f"<b>Conexión Exitosa:</b> {message}<br>"
                f"Servidor: <code>{self.settings.database.host}:{self.settings.database.port}</code> | "
                f"Base de Datos: <code>{self.settings.database.name}</code>"
            )
            self.db_details_label.setStyleSheet("color: #276749; margin-top: 5px; border: none;")
        else:
            self.status_badge.setText("ERROR DE CONEXIÓN")
            self.status_badge.setStyleSheet("background-color: #fed7d7; color: #9b2c2c; padding: 4px 10px; border-radius: 4px; font-weight: bold;")
            self.db_details_label.setText(
                f"<b>Error al conectar con la base de datos:</b><br>{message}<br>"
                "<i>Verifique que el servicio PostgreSQL esté activo y que los parámetros en el archivo .env sean correctos.</i>"
            )
            self.db_details_label.setStyleSheet("color: #c53030; margin-top: 5px; border: none;")

        self.test_btn.setEnabled(True)
