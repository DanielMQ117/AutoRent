"""Ventana principal / Dashboard con navegación modular, RBAC y catálogos de Fase 3."""

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
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import get_settings
from src.core.logger import get_logger
from src.core.session import session
from src.services.auth_service import auth_service
from src.ui.views.clients_view import ClientsView
from src.ui.views.contracts_view import ContractsView
from src.ui.views.reservations_view import ReservationsView
from src.ui.views.vehicles_view import VehiclesView

logger = get_logger(__name__)


class DashboardView(QMainWindow):
    """Dashboard principal con navegación entre módulos de catálogo (Clientes, Flota) y control RBAC."""

    # Señal emitida al solicitar el cierre de sesión
    logout_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.settings = get_settings()
        self._init_ui()

    def _init_ui(self) -> None:
        """Inicializa los componentes de la interfaz de usuario."""
        self.setWindowTitle(f"{self.settings.app.name} — Panel de Control")
        self.resize(1180, 780)
        self.setMinimumSize(1000, 680)
        self.setStyleSheet("background-color: #0f172a; color: #f8fafc;")

        # Widget central con layout vertical
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(14)

        # 1. Barra Superior Persistente de Navegación y Perfil
        top_bar = self._create_top_bar()
        main_layout.addWidget(top_bar)

        # 2. QStackedWidget para alternar entre el Panel General y los Módulos de Catálogo
        self.stacked_widget = QStackedWidget(self)

        # Página 0: Vista General del Dashboard (Banner + Tarjetas RBAC)
        self.dashboard_page = self._create_dashboard_overview_page()
        self.stacked_widget.addWidget(self.dashboard_page)

        # Página 1: Módulo de Gestión de Clientes (Fase 3)
        self.clients_view = ClientsView(self)
        self.clients_view.back_requested.connect(lambda: self._switch_to_page(0))
        self.stacked_widget.addWidget(self.clients_view)

        # Página 2: Módulo de Gestión de Flota & Vehículos (Fase 3)
        self.vehicles_view = VehiclesView(self)
        self.vehicles_view.back_requested.connect(lambda: self._switch_to_page(0))
        self.stacked_widget.addWidget(self.vehicles_view)

        # Página 3: Módulo de Gestión de Reservas (Fase 4)
        self.reservations_view = ReservationsView(self)
        self.reservations_view.back_requested.connect(lambda: self._switch_to_page(0))
        self.stacked_widget.addWidget(self.reservations_view)

        # Página 4: Módulo de Gestión de Contratos y Entrega (Fase 5)
        self.contracts_view = ContractsView(self)
        self.contracts_view.back_requested.connect(lambda: self._switch_to_page(0))
        self.stacked_widget.addWidget(self.contracts_view)

        main_layout.addWidget(self.stacked_widget, stretch=1)

        # 3. Barra de Estado Inferior
        self._setup_status_bar()

    def _create_top_bar(self) -> QFrame:
        """Crea la barra superior con logo, accesos rápidos, perfil y botón de logout."""
        top_bar = QFrame(self)
        top_bar.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 10px 18px;
            }
        """)
        bar_layout = QHBoxLayout(top_bar)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(14)

        # Logo / Marca
        brand_label = QLabel("AutoRent Pro")
        brand_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        brand_label.setStyleSheet("color: #38bdf8; border: none;")
        bar_layout.addWidget(brand_label)

        # Botones de navegación directa entre módulos autorizados
        nav_container = QHBoxLayout()
        nav_container.setSpacing(8)

        self.btn_nav_dash = QPushButton("🏠 Inicio")
        self._style_nav_button(self.btn_nav_dash)
        self.btn_nav_dash.clicked.connect(lambda: self._switch_to_page(0))
        nav_container.addWidget(self.btn_nav_dash)

        if session.has_permission("flota"):
            self.btn_nav_flota = QPushButton("🚗 Flota")
            self._style_nav_button(self.btn_nav_flota)
            self.btn_nav_flota.clicked.connect(lambda: self._open_flota_module())
            nav_container.addWidget(self.btn_nav_flota)

        if session.has_permission("clientes"):
            self.btn_nav_clientes = QPushButton("👥 Clientes")
            self._style_nav_button(self.btn_nav_clientes)
            self.btn_nav_clientes.clicked.connect(lambda: self._open_clientes_module())
            nav_container.addWidget(self.btn_nav_clientes)

        if session.has_permission("reservas"):
            self.btn_nav_reservas = QPushButton("📅 Reservas")
            self._style_nav_button(self.btn_nav_reservas)
            self.btn_nav_reservas.clicked.connect(lambda: self._open_reservations_module())
            nav_container.addWidget(self.btn_nav_reservas)

        if session.has_permission("contratos"):
            self.btn_nav_contratos = QPushButton("📄 Contratos")
            self._style_nav_button(self.btn_nav_contratos)
            self.btn_nav_contratos.clicked.connect(lambda: self._open_contratos_module())
            nav_container.addWidget(self.btn_nav_contratos)

        bar_layout.addLayout(nav_container)
        bar_layout.addStretch()

        # Datos del usuario autenticado
        user = session.current_user
        nombre = user.nombre_completo if user else "Usuario del Sistema"
        username = f"@{user.username}" if user else "@anon"
        rol = session.role_name

        user_info_layout = QVBoxLayout()
        user_info_layout.setSpacing(1)
        user_info_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        name_label = QLabel(nombre)
        name_label.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        name_label.setStyleSheet("color: #f8fafc; border: none;")

        username_label = QLabel(username)
        username_label.setFont(QFont("Segoe UI", 8))
        username_label.setStyleSheet("color: #94a3b8; border: none;")

        user_info_layout.addWidget(name_label)
        user_info_layout.addWidget(username_label)
        bar_layout.addLayout(user_info_layout)

        # Badge del Rol
        role_badge = QLabel(f" {rol} ")
        role_badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        role_color = self._get_role_color(rol)
        role_badge.setStyleSheet(f"""
            background-color: {role_color['bg']};
            color: {role_color['text']};
            border: 1px solid {role_color['border']};
            border-radius: 4px;
            padding: 3px 8px;
        """)
        bar_layout.addWidget(role_badge)

        # Botón Cerrar Sesión
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
                margin-left: 6px;
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

    @staticmethod
    def _style_nav_button(btn: QPushButton) -> None:
        btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #0f172a;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #38bdf8;
                border: 1px solid #38bdf8;
            }
        """)

    def _create_dashboard_overview_page(self) -> QWidget:
        """Construye la página principal del dashboard con el banner y la cuadrícula de módulos."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Banner de bienvenida
        banner = self._create_welcome_banner()
        layout.addWidget(banner)

        # Título de módulos
        section_header = QHBoxLayout()
        section_title = QLabel("Módulos del Sistema:")
        section_title.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        section_title.setStyleSheet("color: #f1f5f9;")

        role_info_badge = QLabel(f"Permisos activos según rol: {session.role_name}")
        role_info_badge.setFont(QFont("Segoe UI", 9))
        role_info_badge.setStyleSheet("color: #94a3b8;")

        section_header.addWidget(section_title)
        section_header.addStretch()
        section_header.addWidget(role_info_badge)
        layout.addLayout(section_header)

        # Scroll con tarjetas de módulos
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
        layout.addWidget(scroll_area, stretch=1)

        return page

    def _create_welcome_banner(self) -> QFrame:
        """Crea el banner informativo de bienvenida al dashboard."""
        banner = QFrame(self)
        banner.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-left: 4px solid #38bdf8;
                border-radius: 8px;
                padding: 14px 18px;
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
            "Fases 3, 4 y 5 activas: Los módulos de 'Gestión de Clientes', 'Gestión de Flota', 'Reservas' y 'Contratos de Entrega' "
            "se encuentran plenamente operativos con formalización transaccional, inspección física y garantías."
        )
        desc_label.setFont(QFont("Segoe UI", 9))
        desc_label.setStyleSheet("color: #94a3b8; border: none;")

        banner_layout.addWidget(welcome_title)
        banner_layout.addWidget(desc_label)
        return banner

    def _render_module_cards(self) -> None:
        """Genera dinámicamente las tarjetas de los módulos aplicando reglas RBAC."""
        modules: List[Tuple[str, str, str, str]] = [
            ("flota", "🚗", "Gestión de Flota", "Catálogo técnico de vehículos, odómetro, combustible y estados (Disponible, Alquilado, Taller)."),
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
            if col >= 4:
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

        is_operativo = module_key in ("flota", "clientes", "reservas", "contratos")

        if has_access:
            badge_color = "#38bdf8" if is_operativo else "#4ade80"
            status_text = "★ Módulo Operativo" if is_operativo else "✓ Acceso Concedido"

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
            status_style = f"color: {badge_color}; font-size: 8pt; font-weight: bold; border: none;"
        else:
            card.setStyleSheet("""
                QFrame {
                    background-color: #0f172a;
                    border: 1px solid #334155;
                    border-radius: 10px;
                }
            """)
            status_text = "🔒 Acceso Restringido"
            status_style = "color: #94a3b8; font-size: 8pt; border: none;"

        # Encabezado
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
        if has_access:
            if module_key in ("flota", "clientes"):
                btn_label = "Abrir Catálogo"
            elif module_key == "reservas":
                btn_label = "Gestionar Reservas"
            elif module_key == "contratos":
                btn_label = "Gestionar Contratos"
            else:
                btn_label = "Abrir Módulo"
        else:
            btn_label = "Restringido"

        action_btn = QPushButton(btn_label)
        action_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        action_btn.setEnabled(has_access)
        action_btn.setCursor(Qt.CursorShape.PointingHandCursor if has_access else Qt.CursorShape.ForbiddenCursor)

        if has_access:
            btn_bg = "#0284c7" if is_operativo else "#334155"
            btn_hover = "#0369a1" if is_operativo else "#475569"
            action_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {btn_bg};
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 7px;
                }}
                QPushButton:hover {{
                    background-color: {btn_hover};
                }}
            """)
            action_btn.clicked.connect(lambda _, n=name, k=module_key: self._handle_open_module(n, k))
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

    def _switch_to_page(self, index: int) -> None:
        """Cambia de vista en el QStackedWidget."""
        self.stacked_widget.setCurrentIndex(index)

    def _open_clientes_module(self) -> None:
        """Abre la pantalla del catálogo de clientes."""
        if not session.has_permission("clientes"):
            QMessageBox.warning(self, "Acceso Restringido", "Su perfil no cuenta con permisos para el módulo de Clientes.")
            return
        self.clients_view.load_data()
        self._switch_to_page(1)

    def _open_flota_module(self) -> None:
        """Abre la pantalla del catálogo de flota y vehículos."""
        if not session.has_permission("flota"):
            QMessageBox.warning(self, "Acceso Restringido", "Su perfil no cuenta con permisos para el módulo de Flota.")
            return
        self.vehicles_view.load_data()
        self._switch_to_page(2)

    def _open_reservations_module(self) -> None:
        """Abre la pantalla del motor de reservas y disponibilidad."""
        if not session.has_permission("reservas"):
            QMessageBox.warning(self, "Acceso Restringido", "Su perfil no cuenta con permisos para el módulo de Reservas.")
            return
        self.reservations_view.load_data()
        self._switch_to_page(3)

    def _open_contratos_module(self) -> None:
        """Abre la pantalla de gestión de contratos y entrega de vehículos."""
        if not session.has_permission("contratos"):
            QMessageBox.warning(self, "Acceso Restringido", "Su perfil no cuenta con permisos para el módulo de Contratos.")
            return
        self.contracts_view.load_data()
        self._switch_to_page(4)

    def _handle_open_module(self, module_name: str, module_key: str) -> None:
        """Maneja el clic en las tarjetas de módulo."""
        if module_key == "clientes":
            self._open_clientes_module()
        elif module_key == "flota":
            self._open_flota_module()
        elif module_key == "reservas":
            self._open_reservations_module()
        elif module_key == "contratos":
            self._open_contratos_module()
        else:
            QMessageBox.information(
                self,
                module_name,
                f"El módulo '{module_name}' se encuentra autorizado para su perfil.\n\n"
                "La lógica de este flujo transaccional será implementada en las siguientes fases del proyecto.",
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
