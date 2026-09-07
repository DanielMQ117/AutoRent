"""Ventana principal / Dashboard provisional con protección de módulos según rol (RBAC)."""

from datetime import datetime
from typing import List, Tuple
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import get_settings
from src.core.logger import get_logger
from src.core.session import session
from src.services.auth_service import auth_service

logger = get_logger(__name__)


class DashboardView(QMainWindow):
    """Dashboard provisional que aplica control de acceso y protección de módulos por rol."""

    # Señal emitida al solicitar el cierre de sesión
    logout_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.settings = get_settings()
        self._init_ui()

    def _init_ui(self) -> None:
        """Inicializa los componentes de la interfaz de usuario."""
        self.setWindowTitle(f"{self.settings.app.name} — Panel de Control")
        self.resize(1100, 720)
        self.setMinimumSize(950, 600)
        self.setStyleSheet("background-color: #0f172a; color: #f8fafc;")

        # Widget central con scroll
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(20)

        # 1. Barra Superior de Navegación y Perfil de Usuario
        top_bar = self._create_top_bar()
        main_layout.addWidget(top_bar)

        # 2. Banner de Bienvenida
        banner = self._create_welcome_banner()
        main_layout.addWidget(banner)

        # 3. Título de la sección de módulos
        section_header = QHBoxLayout()
        section_title = QLabel("Módulos del Sistema:")
        section_title.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        section_title.setStyleSheet("color: #f1f5f9;")

        role_info_badge = QLabel(f"Permisos asignados según rol: {session.role_name}")
        role_info_badge.setFont(QFont("Segoe UI", 9))
        role_info_badge.setStyleSheet("color: #94a3b8;")

        section_header.addWidget(section_title)
        section_header.addStretch()
        section_header.addWidget(role_info_badge)
        main_layout.addLayout(section_header)

        # 4. Cuadrícula de Módulos con Protección RBAC
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        modules_container = QWidget()
        modules_container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(modules_container)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        self._render_module_cards()

        scroll_area.setWidget(modules_container)
        main_layout.addWidget(scroll_area, stretch=1)

        # 5. Barra de Estado Inferior
        self._setup_status_bar()

    def _create_top_bar(self) -> QFrame:
        """Crea la barra superior con información del usuario y botón de logout."""
        top_bar = QFrame(self)
        top_bar.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 12px 20px;
            }
        """)
        bar_layout = QHBoxLayout(top_bar)
        bar_layout.setContentsMargins(0, 0, 0, 0)

        # Logo / Título
        brand_label = QLabel("AutoRent Pro")
        brand_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        brand_label.setStyleSheet("color: #38bdf8; border: none;")
        bar_layout.addWidget(brand_label)

        bar_layout.addStretch()

        # Datos del usuario autenticado
        user = session.current_user
        nombre = user.nombre_completo if user else "Usuario del Sistema"
        username = f"@{user.username}" if user else "@anon"
        rol = session.role_name

        user_info_layout = QVBoxLayout()
        user_info_layout.setSpacing(2)
        user_info_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        name_label = QLabel(nombre)
        name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        name_label.setStyleSheet("color: #f8fafc; border: none;")

        username_label = QLabel(username)
        username_label.setFont(QFont("Segoe UI", 8))
        username_label.setStyleSheet("color: #94a3b8; border: none;")

        user_info_layout.addWidget(name_label)
        user_info_layout.addWidget(username_label)
        bar_layout.addLayout(user_info_layout)

        # Badge del Rol
        role_badge = QLabel(f" {rol} ")
        role_badge.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        role_color = self._get_role_color(rol)
        role_badge.setStyleSheet(f"""
            background-color: {role_color['bg']};
            color: {role_color['text']};
            border: 1px solid {role_color['border']};
            border-radius: 6px;
            padding: 4px 10px;
        """)
        bar_layout.addWidget(role_badge)

        # Botón de Cerrar Sesión (Logout)
        logout_btn = QPushButton("Cerrar Sesión")
        logout_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #e2e8f0;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 6px 14px;
                margin-left: 10px;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: #ffffff;
                border: 1px solid #dc2626;
            }
        """)
        logout_btn.clicked.connect(self._handle_logout)
        bar_layout.addWidget(logout_btn)

        return top_bar

    def _create_welcome_banner(self) -> QFrame:
        """Crea el banner informativo de bienvenida al dashboard."""
        banner = QFrame(self)
        banner.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-left: 4px solid #38bdf8;
                border-radius: 8px;
                padding: 16px 20px;
            }
        """)
        banner_layout = QVBoxLayout(banner)
        banner_layout.setSpacing(4)
        banner_layout.setContentsMargins(0, 0, 0, 0)

        user = session.current_user
        nombre = user.nombre_completo if user else "Usuario"

        welcome_title = QLabel(f"Bienvenido(a), {nombre}")
        welcome_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        welcome_title.setStyleSheet("color: #f8fafc; border: none;")

        desc_label = QLabel(
            "El sistema de autenticación y control de permisos (RBAC) está activo. "
            "Los módulos a los que tiene acceso se encuentran resaltados. Los módulos restringidos aparecen bloqueados."
        )
        desc_label.setFont(QFont("Segoe UI", 9))
        desc_label.setStyleSheet("color: #94a3b8; border: none;")

        banner_layout.addWidget(welcome_title)
        banner_layout.addWidget(desc_label)
        return banner

    def _render_module_cards(self) -> None:
        """Genera dinámicamente las tarjetas de los módulos aplicando reglas RBAC."""
        # Definición de módulos del sistema: (Clave_Permiso, Icono, Nombre, Descripción)
        modules: List[Tuple[str, str, str, str]] = [
            ("flota", "🚗", "Gestión de Flota", "Administración de vehículos, marcas, modelos, kilometraje y categorías."),
            ("clientes", "👥", "Gestión de Clientes", "Expedientes de clientes, licencias de conducir y estatus crediticio."),
            ("reservas", "📅", "Reservas", "Calendario de disponibilidad, bloqueo de categorías y registro de anticipos."),
            ("contratos", "📄", "Contratos y Entrega", "Apertura de contratos, pólizas de seguro, garantías e inspección de salida."),
            ("devoluciones", "🔄", "Devoluciones e Inspección", "Recepción física del vehículo, cálculo de odómetro y registro de averías."),
            ("mantenimientos", "🔧", "Mantenimiento y Taller", "Órdenes de taller preventivo y correctivo, gastos y reincorporación."),
            ("reportes", "📊", "Reportes Financieros", "Balances de ingresos, ocupación de flota, penalizaciones y auditoría."),
            ("usuarios", "🔐", "Control de Usuarios", "Administración de cuentas de acceso, asignación de roles y permisos."),
        ]

        row, col = 0, 0
        for key, icon, name, desc in modules:
            has_access = session.has_permission(key)
            card = self._create_module_card(key, icon, name, desc, has_access)
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col >= 4:  # 4 columnas por fila
                col = 0
                row += 1

    def _create_module_card(
        self,
        module_key: str,
        icon: str,
        name: str,
        description: str,
        has_access: bool,
    ) -> QFrame:
        """Crea una tarjeta visual individual con estados diferenciados por permisos."""
        card = QFrame()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)
        card_layout.setContentsMargins(16, 16, 16, 16)

        if has_access:
            # Estilo: Módulo Autorizado
            card.setStyleSheet("""
                QFrame {
                    background-color: #1e293b;
                    border: 1px solid #38bdf8;
                    border-radius: 10px;
                }
                QFrame:hover {
                    background-color: #243247;
                    border: 1px solid #7dd3fc;
                }
            """)
            status_text = "✓ Acceso Concedido"
            status_style = "color: #4ade80; font-size: 8pt; font-weight: bold; border: none;"
        else:
            # Estilo: Módulo Bloqueado (Muted / Opacity reducida)
            card.setStyleSheet("""
                QFrame {
                    background-color: #0f172a;
                    border: 1px solid #334155;
                    border-radius: 10px;
                }
            """)
            status_text = "🔒 Acceso Restringido"
            status_style = "color: #94a3b8; font-size: 8pt; border: none;"

        # Encabezado de la tarjeta con Icono y Badge
        header = QHBoxLayout()
        icon_label = QLabel(icon if has_access else "🔒")
        icon_label.setFont(QFont("Segoe UI Emoji", 20))
        icon_label.setStyleSheet("border: none;")

        status_badge = QLabel(status_text)
        status_badge.setFont(QFont("Segoe UI", 8))
        status_badge.setStyleSheet(status_style)

        header.addWidget(icon_label)
        header.addStretch()
        header.addWidget(status_badge)
        card_layout.addLayout(header)

        # Nombre del Módulo
        title = QLabel(name)
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title_color = "#f8fafc" if has_access else "#64748b"
        title.setStyleSheet(f"color: {title_color}; border: none;")
        card_layout.addWidget(title)

        # Descripción breve
        desc = QLabel(description)
        desc.setFont(QFont("Segoe UI", 8))
        desc.setWordWrap(True)
        desc_color = "#94a3b8" if has_access else "#475569"
        desc.setStyleSheet(f"color: {desc_color}; border: none;")
        card_layout.addWidget(desc, stretch=1)

        # Botón de Acción
        action_btn = QPushButton("Abrir Módulo" if has_access else "Restringido")
        action_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        action_btn.setEnabled(has_access)
        action_btn.setCursor(Qt.CursorShape.PointingHandCursor if has_access else Qt.CursorShape.ForbiddenCursor)

        if has_access:
            action_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0284c7;
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 7px;
                }
                QPushButton:hover {
                    background-color: #0369a1;
                }
            """)
            action_btn.clicked.connect(lambda _, n=name: self._handle_open_module(n))
        else:
            action_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1e293b;
                    color: #475569;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 7px;
                }
            """)

        card_layout.addWidget(action_btn)
        return card

    def _handle_open_module(self, module_name: str) -> None:
        """Maneja el clic en un módulo accesible (en esta fase solo notifica que está preparado)."""
        QMessageBox.information(
            self,
            module_name,
            f"El módulo '{module_name}' se encuentra autorizado para su perfil.\n\n"
            "La lógica de este módulo de negocio será implementada en las siguientes fases del proyecto.",
        )

    def _handle_logout(self) -> None:
        """Confirma y procesa el cierre de sesión."""
        reply = QMessageBox.question(
            self,
            "Cerrar Sesión",
            "¿Está seguro de que desea salir del sistema?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            logger.info("Cerrando sesión a petición del usuario...")
            auth_service.logout()
            self.logout_requested.emit()

    def _setup_status_bar(self) -> None:
        """Configura la barra de estado inferior."""
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)
        status_bar.setStyleSheet("background-color: #1e293b; color: #94a3b8; border-top: 1px solid #334155;")

        login_time_str = session.login_time.strftime("%H:%M:%S") if session.login_time else "--:--"
        status_bar.showMessage(
            f"Sesión iniciada a las: {login_time_str} | Base de datos: {self.settings.database.name} ({self.settings.database.host}) | Entorno: {self.settings.app.env.upper()}"
        )

    @staticmethod
    def _get_role_color(role_name: str) -> dict:
        """Retorna la paleta de colores para el badge de cada rol."""
        colors = {
            "ADMINISTRADOR": {"bg": "rgba(168, 85, 247, 0.15)", "text": "#c084fc", "border": "rgba(168, 85, 247, 0.3)"},
            "GERENTE": {"bg": "rgba(34, 197, 94, 0.15)", "text": "#4ade80", "border": "rgba(34, 197, 94, 0.3)"},
            "AGENTE_VENTAS": {"bg": "rgba(56, 189, 248, 0.15)", "text": "#38bdf8", "border": "rgba(56, 189, 248, 0.3)"},
            "INSPECTOR_TALLER": {"bg": "rgba(249, 115, 22, 0.15)", "text": "#fb923c", "border": "rgba(249, 115, 22, 0.3)"},
        }
        return colors.get(role_name, {"bg": "rgba(148, 163, 184, 0.15)", "text": "#94a3b8", "border": "rgba(148, 163, 184, 0.3)"})
