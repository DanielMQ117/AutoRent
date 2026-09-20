"""Vista principal para la Administración de Usuarios, Roles RBAC y Auditoría (Fase 10)."""

from datetime import datetime
from typing import List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.exceptions import AppException
from src.core.logger import get_logger
from src.core.session import ROLE_MODULE_PERMISSIONS, session
from src.domain.enums import UserRole
from src.domain.models import AuditLog, Role, User
from src.services.user_service import user_service
from src.ui.components.badges import create_badge, get_user_role_badge, get_user_status_badge
from src.ui.views.user_form_dialog import UserFormDialog
from src.ui.views.user_password_dialog import UserPasswordDialog

logger = get_logger(__name__)


class UsersView(QWidget):
    """Pantalla integral de control de usuarios, gestión de privilegios y bitácora de auditoría."""

    back_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.users_list: List[User] = []
        self.audit_logs: List[AuditLog] = []
        self._init_ui()
        self.load_data()

    def _init_ui(self) -> None:
        """Construye los componentes visuales de la vista de usuarios."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(14)

        # 1. Cabecera con botón volver, título y acción
        header_layout = QHBoxLayout()

        self.btn_back = QPushButton("← Volver al Panel")
        self.btn_back.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #e2e8f0;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #475569;
                color: #ffffff;
            }
        """)
        self.btn_back.clicked.connect(self.back_requested.emit)
        header_layout.addWidget(self.btn_back)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        title = QLabel("Control de Usuarios, Roles RBAC y Auditoría")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #f8fafc;")

        subtitle = QLabel("Administración de credenciales de acceso, control de privilegios basados en roles y trazabilidad (Fase 10).")
        subtitle.setFont(QFont("Segoe UI", 9))
        subtitle.setStyleSheet("color: #94a3b8;")
        title_vbox.addWidget(title)
        title_vbox.addWidget(subtitle)
        header_layout.addLayout(title_vbox)

        header_layout.addStretch()

        self.btn_refresh = QPushButton("🔄 Refrescar")
        self.btn_refresh.setFont(QFont("Segoe UI", 9))
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 14px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #f8fafc;
            }
        """)
        self.btn_refresh.clicked.connect(self.load_data)
        header_layout.addWidget(self.btn_refresh)

        self.btn_new_user = QPushButton("👤 + Nuevo Usuario")
        self.btn_new_user.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_new_user.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_user.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
            QPushButton:pressed {
                background-color: #075985;
            }
        """)
        self.btn_new_user.clicked.connect(self._open_new_user_dialog)
        header_layout.addWidget(self.btn_new_user)

        main_layout.addLayout(header_layout)

        # 2. Métricas / KPIs
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(12)

        self.card_total = self._create_kpi_card("Total Cuentas", "0", "#38bdf8")
        self.card_activos = self._create_kpi_card("Cuentas Activas", "0", "#34d399")
        self.card_inactivos = self._create_kpi_card("Cuentas Bloqueadas", "0", "#f87171")
        self.card_roles = self._create_kpi_card("Roles del Sistema", "4", "#c084fc")

        kpi_layout.addWidget(self.card_total)
        kpi_layout.addWidget(self.card_activos)
        kpi_layout.addWidget(self.card_inactivos)
        kpi_layout.addWidget(self.card_roles)
        main_layout.addLayout(kpi_layout)

        # 3. Pestañas de Navegación
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #334155;
                background-color: #0f172a;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #1e293b;
                color: #94a3b8;
                padding: 9px 20px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
                font-size: 9pt;
            }
            QTabBar::tab:selected {
                background-color: #0284c7;
                color: #ffffff;
            }
            QTabBar::tab:hover:!selected {
                background-color: #334155;
                color: #e2e8f0;
            }
        """)

        # Pestaña 1: Cuentas y Accesos
        self.tab_users = self._create_users_tab()
        self.tabs.addTab(self.tab_users, "👥 Cuentas de Acceso")

        # Pestaña 2: Matriz RBAC
        self.tab_rbac = self._create_rbac_tab()
        self.tabs.addTab(self.tab_rbac, "🛡️ Matriz de Privilegios RBAC")

        # Pestaña 3: Bitácora de Auditoría
        self.tab_audit = self._create_audit_tab()
        self.tabs.addTab(self.tab_audit, "📜 Bitácora de Auditoría (RF-05)")

        self.tabs.currentChanged.connect(self._on_tab_changed)
        main_layout.addWidget(self.tabs, stretch=1)

    def _create_kpi_card(self, title: str, initial_value: str, accent_color: str) -> QFrame:
        """Genera una tarjeta estilizada para métricas."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #1e293b;
                border: 1px solid #334155;
                border-left: 4px solid {accent_color};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(2)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl_title = QLabel(title.upper())
        lbl_title.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #94a3b8;")

        lbl_val = QLabel(initial_value)
        lbl_val.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_val.setStyleSheet(f"color: {accent_color};")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        card.val_label = lbl_val  # type: ignore
        return card

    # =========================================================================
    # PESTAÑA 1: GESTIÓN DE USUARIOS
    # =========================================================================
    def _create_users_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Barra de Búsqueda y Filtros
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Buscar por usuario, nombre completo o correo...")
        self.txt_search.setStyleSheet("""
            QLineEdit {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 12px;
                font-size: 9pt;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
            }
        """)
        self.txt_search.textChanged.connect(self._apply_user_filters)
        filter_bar.addWidget(self.txt_search, stretch=2)

        self.cmb_role_filter = QComboBox()
        self.cmb_role_filter.setStyleSheet("""
            QComboBox {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                min-width: 140px;
            }
        """)
        self.cmb_role_filter.addItem("Todos los Roles", userData=None)
        self.cmb_role_filter.addItem("ADMINISTRADOR", userData=1)
        self.cmb_role_filter.addItem("AGENTE_VENTAS", userData=2)
        self.cmb_role_filter.addItem("INSPECTOR_TALLER", userData=3)
        self.cmb_role_filter.addItem("GERENTE", userData=4)
        self.cmb_role_filter.currentIndexChanged.connect(self._apply_user_filters)
        filter_bar.addWidget(self.cmb_role_filter)

        self.cmb_status_filter = QComboBox()
        self.cmb_status_filter.setStyleSheet("""
            QComboBox {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                min-width: 130px;
            }
        """)
        self.cmb_status_filter.addItem("Todos los Estados", userData=None)
        self.cmb_status_filter.addItem("Solo Activos", userData=True)
        self.cmb_status_filter.addItem("Solo Inactivos", userData=False)
        self.cmb_status_filter.currentIndexChanged.connect(self._apply_user_filters)
        filter_bar.addWidget(self.cmb_status_filter)

        layout.addLayout(filter_bar)

        # Tabla de Usuarios
        self.tbl_users = QTableWidget()
        self.tbl_users.setColumnCount(7)
        self.tbl_users.setHorizontalHeaderLabels([
            "ID",
            "Usuario",
            "Nombre Completo",
            "Correo Electrónico",
            "Rol Asignado",
            "Estado",
            "Fecha Registro",
        ])
        self.tbl_users.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tbl_users.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tbl_users.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tbl_users.horizontalHeader().setStretchLastSection(False)
        self.tbl_users.verticalHeader().setVisible(False)
        self.tbl_users.verticalHeader().setDefaultSectionSize(42)
        self.tbl_users.setColumnWidth(0, 50)   # ID
        self.tbl_users.setColumnWidth(1, 120)  # Usuario
        self.tbl_users.setColumnWidth(4, 160)  # Rol Asignado
        self.tbl_users.setColumnWidth(5, 120)  # Estado
        self.tbl_users.setColumnWidth(6, 140)  # Fecha Registro
        self.tbl_users.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_users.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl_users.setAlternatingRowColors(True)
        self.tbl_users.setStyleSheet("""
            QTableWidget {
                background-color: #0f172a;
                alternate-background-color: #1e293b;
                color: #f8fafc;
                gridline-color: #334155;
                border: 1px solid #334155;
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #1e293b;
                color: #94a3b8;
                padding: 8px;
                border: 1px solid #334155;
                font-weight: bold;
                font-size: 9pt;
            }
            QTableWidget::item:selected {
                background-color: #0369a1;
                color: #ffffff;
            }
        """)
        self.tbl_users.itemDoubleClicked.connect(lambda: self._open_edit_user_dialog())
        layout.addWidget(self.tbl_users, stretch=1)

        # Barra de Acciones para el Registro Seleccionado
        actions_bar = QHBoxLayout()
        actions_bar.setSpacing(10)

        self.btn_edit = QPushButton("✏️ Editar Perfil")
        self._style_action_btn(self.btn_edit, "#334155", "#475569")
        self.btn_edit.clicked.connect(self._open_edit_user_dialog)
        actions_bar.addWidget(self.btn_edit)

        self.btn_password = QPushButton("🔑 Restablecer Contraseña")
        self._style_action_btn(self.btn_password, "#0284c7", "#0369a1")
        self.btn_password.clicked.connect(self._open_password_dialog)
        actions_bar.addWidget(self.btn_password)

        self.btn_toggle_status = QPushButton("⚡ Conmutar Estado")
        self._style_action_btn(self.btn_toggle_status, "#d97706", "#b45309")
        self.btn_toggle_status.clicked.connect(self._handle_toggle_status)
        actions_bar.addWidget(self.btn_toggle_status)

        self.btn_unlock = QPushButton("🔓 Desbloquear Cuenta")
        self._style_action_btn(self.btn_unlock, "#059669", "#047857")
        self.btn_unlock.clicked.connect(self._handle_unlock)
        actions_bar.addWidget(self.btn_unlock)

        self.btn_delete = QPushButton("🗑️ Eliminar")
        self._style_action_btn(self.btn_delete, "#dc2626", "#b91c1c")
        self.btn_delete.clicked.connect(self._handle_delete_user)
        actions_bar.addWidget(self.btn_delete)

        actions_bar.addStretch()
        layout.addLayout(actions_bar)

        return widget

    def _style_action_btn(self, btn: QPushButton, bg_color: str, hover_color: str) -> None:
        btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 7px 14px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """)

    # =========================================================================
    # PESTAÑA 2: MATRIZ RBAC
    # =========================================================================
    def _create_rbac_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        info_header = QLabel("Matriz de Asignación de Privilegios por Perfil Operativo")
        info_header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        info_header.setStyleSheet("color: #38bdf8;")
        layout.addWidget(info_header)

        desc = QLabel(
            "El sistema aplica un estricto modelo de Control de Acceso Basado en Roles (RBAC). "
            "Cada rol delimita la visibilidad y capacidad operativa en los módulos del sistema."
        )
        desc.setFont(QFont("Segoe UI", 9))
        desc.setStyleSheet("color: #94a3b8;")
        layout.addWidget(desc)

        # Tabla de la Matriz RBAC
        self.tbl_rbac = QTableWidget()
        modules = [
            ("flota", "🚗 Flota"),
            ("clientes", "👥 Clientes"),
            ("reservas", "📅 Reservas"),
            ("contratos", "📄 Contratos"),
            ("devoluciones", "🔄 Devoluciones"),
            ("mantenimientos", "🔧 Taller"),
            ("reportes", "📊 Reportes"),
            ("usuarios", "🔐 Usuarios"),
        ]
        roles = [
            UserRole.ADMINISTRADOR.value,
            UserRole.GERENTE.value,
            UserRole.AGENTE_VENTAS.value,
            UserRole.INSPECTOR_TALLER.value,
        ]

        self.tbl_rbac.setColumnCount(len(modules) + 1)
        headers = ["Rol del Sistema"] + [m[1] for m in modules]
        self.tbl_rbac.setHorizontalHeaderLabels(headers)
        self.tbl_rbac.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_rbac.verticalHeader().setVisible(False)
        self.tbl_rbac.verticalHeader().setDefaultSectionSize(44)
        self.tbl_rbac.setRowCount(len(roles))
        self.tbl_rbac.setStyleSheet("""
            QTableWidget {
                background-color: #0f172a;
                alternate-background-color: #1e293b;
                color: #f8fafc;
                gridline-color: #334155;
                border: 1px solid #334155;
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #1e293b;
                color: #94a3b8;
                padding: 10px;
                border: 1px solid #334155;
                font-weight: bold;
                font-size: 9pt;
            }
        """)

        for row_idx, r_name in enumerate(roles):
            role_badge = get_user_role_badge(r_name)
            self.tbl_rbac.setCellWidget(row_idx, 0, role_badge)

            allowed_set = ROLE_MODULE_PERMISSIONS.get(r_name, set())
            for col_idx, (m_key, _) in enumerate(modules, start=1):
                has_perm = m_key in allowed_set
                if has_perm:
                    badge = create_badge("✓ AUTORIZADO", "rgba(16, 185, 129, 0.15)", "#34d399", "rgba(16, 185, 129, 0.4)")
                else:
                    badge = create_badge("✕ DENEGADO", "rgba(239, 68, 68, 0.12)", "#f87171", "rgba(239, 68, 68, 0.3)")
                self.tbl_rbac.setCellWidget(row_idx, col_idx, badge)

        layout.addWidget(self.tbl_rbac, stretch=1)
        return widget

    # =========================================================================
    # PESTAÑA 3: BITÁCORA DE AUDITORÍA (RF-05)
    # =========================================================================
    def _create_audit_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Filtros de auditoría
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        self.txt_audit_user = QLineEdit()
        self.txt_audit_user.setPlaceholderText("🔍 Filtrar por usuario ejecutor...")
        self.txt_audit_user.setStyleSheet("""
            QLineEdit {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 12px;
                font-size: 9pt;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
            }
        """)
        self.txt_audit_user.textChanged.connect(self._apply_audit_filters)
        filter_bar.addWidget(self.txt_audit_user, stretch=2)

        self.cmb_audit_action = QComboBox()
        self.cmb_audit_action.setStyleSheet("""
            QComboBox {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                min-width: 170px;
            }
        """)
        self.cmb_audit_action.addItem("Todas las Acciones", userData=None)
        self.cmb_audit_action.addItem("LOGIN_EXITOSO", userData="LOGIN_EXITOSO")
        self.cmb_audit_action.addItem("LOGOUT", userData="LOGOUT")
        self.cmb_audit_action.addItem("BLOQUEO_AUTOMATICO_INTENTOS", userData="BLOQUEO_AUTOMATICO_INTENTOS")
        self.cmb_audit_action.addItem("CREAR_USUARIO", userData="CREAR_USUARIO")
        self.cmb_audit_action.addItem("ACTUALIZAR_USUARIO", userData="ACTUALIZAR_USUARIO")
        self.cmb_audit_action.addItem("CAMBIO_ESTADO_USUARIO", userData="CAMBIO_ESTADO_USUARIO")
        self.cmb_audit_action.addItem("DESBLOQUEAR_CUENTA", userData="DESBLOQUEAR_CUENTA")
        self.cmb_audit_action.addItem("RESETEO_PASSWORD", userData="RESETEO_PASSWORD")
        self.cmb_audit_action.addItem("ELIMINAR_USUARIO", userData="ELIMINAR_USUARIO")
        self.cmb_audit_action.currentIndexChanged.connect(self._apply_audit_filters)
        filter_bar.addWidget(self.cmb_audit_action)

        btn_refresh_audit = QPushButton("🔄 Actualizar Bitácora")
        self._style_action_btn(btn_refresh_audit, "#0284c7", "#0369a1")
        btn_refresh_audit.clicked.connect(self._load_audit_data)
        filter_bar.addWidget(btn_refresh_audit)

        layout.addLayout(filter_bar)

        # Tabla de Auditoría
        self.tbl_audit = QTableWidget()
        self.tbl_audit.setColumnCount(8)
        self.tbl_audit.setHorizontalHeaderLabels([
            "ID Log",
            "Fecha y Hora",
            "Usuario",
            "Acción Crítica",
            "Módulo / Entidad",
            "ID Reg.",
            "Detalles de la Operación",
            "IP Origen",
        ])
        self.tbl_audit.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tbl_audit.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.tbl_audit.horizontalHeader().setStretchLastSection(False)
        self.tbl_audit.verticalHeader().setVisible(False)
        self.tbl_audit.verticalHeader().setDefaultSectionSize(40)
        self.tbl_audit.setColumnWidth(0, 65)   # ID Log
        self.tbl_audit.setColumnWidth(1, 135)  # Fecha y Hora
        self.tbl_audit.setColumnWidth(2, 110)  # Usuario
        self.tbl_audit.setColumnWidth(3, 160)  # Acción Crítica
        self.tbl_audit.setColumnWidth(4, 130)  # Módulo / Entidad
        self.tbl_audit.setColumnWidth(5, 75)   # ID Reg.
        self.tbl_audit.setColumnWidth(7, 110)  # IP Origen
        self.tbl_audit.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_audit.setAlternatingRowColors(True)
        self.tbl_audit.setStyleSheet("""
            QTableWidget {
                background-color: #0f172a;
                alternate-background-color: #1e293b;
                color: #f8fafc;
                gridline-color: #334155;
                border: 1px solid #334155;
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #1e293b;
                color: #94a3b8;
                padding: 8px;
                border: 1px solid #334155;
                font-weight: bold;
                font-size: 9pt;
            }
            QTableWidget::item:selected {
                background-color: #0369a1;
                color: #ffffff;
            }
        """)
        layout.addWidget(self.tbl_audit, stretch=1)

        return widget

    def _on_tab_changed(self, index: int) -> None:
        """Carga datos específicos al conmutar de pestaña."""
        if index == 2:
            self._load_audit_data()

    # =========================================================================
    # CARGA DE DATOS Y RENDERIZADO
    # =========================================================================
    def load_data(self) -> None:
        """Carga usuarios, métricas e historial de auditoría."""
        self._load_kpis()
        self._apply_user_filters()
        if self.tabs.currentIndex() == 2:
            self._load_audit_data()

    def _load_kpis(self) -> None:
        """Actualiza las tarjetas métricas."""
        try:
            kpis = user_service.get_kpis()
            self.card_total.val_label.setText(str(kpis.get("total", 0)))  # type: ignore
            self.card_activos.val_label.setText(str(kpis.get("activos", 0)))  # type: ignore
            self.card_inactivos.val_label.setText(str(kpis.get("inactivos", 0)))  # type: ignore
            self.card_roles.val_label.setText(str(kpis.get("roles", 4)))  # type: ignore
        except Exception as e:
            logger.warning("Fallo al cargar KPIs de usuarios: %s", e)

    def _apply_user_filters(self) -> None:
        """Consulta y renderiza los usuarios aplicando filtros de UI."""
        search = self.txt_search.text().strip() or None
        id_rol = self.cmb_role_filter.currentData()
        activo = self.cmb_status_filter.currentData()

        try:
            self.users_list = user_service.list_users(search=search, id_rol=id_rol, activo=activo)
            self._render_users_table(self.users_list)
        except Exception as e:
            logger.error("Error al consultar usuarios: %s", e)
            QMessageBox.critical(self, "Error", f"No se pudo cargar la lista de usuarios: {e}")

    def _render_users_table(self, users: List[User]) -> None:
        """Puebla la tabla de usuarios."""
        self.tbl_users.setRowCount(len(users))

        for row, u in enumerate(users):
            # 0. ID
            item_id = QTableWidgetItem(str(u.id_usuario or ""))
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_id.setData(Qt.ItemDataRole.UserRole, u.id_usuario)
            self.tbl_users.setItem(row, 0, item_id)

            # 1. Username
            item_user = QTableWidgetItem(f"@{u.username}")
            item_user.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.tbl_users.setItem(row, 1, item_user)

            # 2. Nombre Completo
            self.tbl_users.setItem(row, 2, QTableWidgetItem(u.nombre_completo))

            # 3. Email
            self.tbl_users.setItem(row, 3, QTableWidgetItem(u.email))

            # 4. Rol
            role_badge = get_user_role_badge(u.rol_nombre or "")
            self.tbl_users.setCellWidget(row, 4, role_badge)

            # 5. Estado
            status_badge = get_user_status_badge(u.activo)
            self.tbl_users.setCellWidget(row, 5, status_badge)

            # 6. Fecha Registro
            fecha_str = u.fecha_creacion.strftime("%Y-%m-%d %H:%M") if u.fecha_creacion else "—"
            item_fecha = QTableWidgetItem(fecha_str)
            item_fecha.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tbl_users.setItem(row, 6, item_fecha)

    def _load_audit_data(self) -> None:
        """Carga y renderiza los logs de auditoría."""
        accion = self.cmb_audit_action.currentData()
        username = self.txt_audit_user.text().strip() or None

        try:
            self.audit_logs = user_service.get_audit_logs(limit=150, accion=accion, username=username)
            self._render_audit_table(self.audit_logs)
        except Exception as e:
            logger.error("Error al consultar bitácora de auditoría: %s", e)

    def _apply_audit_filters(self) -> None:
        """Aplica filtros a la bitácora de auditoría."""
        self._load_audit_data()

    def _render_audit_table(self, logs: List[AuditLog]) -> None:
        """Puebla la tabla de auditoría con badges."""
        self.tbl_audit.setRowCount(len(logs))

        for row, log in enumerate(logs):
            item_id = QTableWidgetItem(str(log.id_auditoria))
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tbl_audit.setItem(row, 0, item_id)

            fecha_str = log.fecha_registro.strftime("%Y-%m-%d %H:%M:%S") if log.fecha_registro else "—"
            item_fecha = QTableWidgetItem(fecha_str)
            item_fecha.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tbl_audit.setItem(row, 1, item_fecha)

            item_user = QTableWidgetItem(f"@{log.username}")
            item_user.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
            self.tbl_audit.setItem(row, 2, item_user)

            # Acción estilizada
            action_badge = self._get_action_badge(log.accion)
            self.tbl_audit.setCellWidget(row, 3, action_badge)

            item_tabla = QTableWidgetItem(log.tabla_afectada.upper())
            item_tabla.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tbl_audit.setItem(row, 4, item_tabla)

            item_reg = QTableWidgetItem(str(log.id_registro or "—"))
            item_reg.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tbl_audit.setItem(row, 5, item_reg)

            self.tbl_audit.setItem(row, 6, QTableWidgetItem(log.detalles or ""))

            item_ip = QTableWidgetItem(log.ip_origen)
            item_ip.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tbl_audit.setItem(row, 7, item_ip)

    def _get_action_badge(self, accion: str) -> QLabel:
        """Retorna un badge visual representativo para cada tipo de acción."""
        act = (accion or "").upper()
        if "LOGIN" in act:
            return create_badge(act, "rgba(16, 185, 129, 0.15)", "#34d399", "rgba(16, 185, 129, 0.4)")
        elif "BLOQUEO" in act or "ELIMINAR" in act:
            return create_badge(act, "rgba(239, 68, 68, 0.15)", "#f87171", "rgba(239, 68, 68, 0.4)")
        elif "CREAR" in act or "DESBLOQUEAR" in act:
            return create_badge(act, "rgba(56, 189, 248, 0.15)", "#38bdf8", "rgba(56, 189, 248, 0.4)")
        elif "PASSWORD" in act or "CAMBIO_ESTADO" in act:
            return create_badge(act, "rgba(245, 158, 11, 0.15)", "#fbbf24", "rgba(245, 158, 11, 0.4)")
        return create_badge(act, "rgba(148, 163, 184, 0.15)", "#cbd5e1", "rgba(148, 163, 184, 0.3)")

    # =========================================================================
    # ACCIONES DEL CRUD
    # =========================================================================
    def _get_selected_user(self) -> Optional[User]:
        """Obtiene la entidad User de la fila actualmente seleccionada."""
        selected_rows = self.tbl_users.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Selección Requerida", "Por favor seleccione un usuario de la lista.")
            return None

        row = selected_rows[0].row()
        item_id = self.tbl_users.item(row, 0)
        if not item_id:
            return None

        user_id = item_id.data(Qt.ItemDataRole.UserRole)
        for u in self.users_list:
            if u.id_usuario == user_id:
                return u
        return None

    def _open_new_user_dialog(self) -> None:
        """Abre el diálogo para registrar un nuevo usuario."""
        dialog = UserFormDialog(parent=self)
        if dialog.exec():
            self.load_data()

    def _open_edit_user_dialog(self) -> None:
        """Abre el diálogo para editar el usuario seleccionado."""
        user = self._get_selected_user()
        if not user:
            return
        dialog = UserFormDialog(user=user, parent=self)
        if dialog.exec():
            self.load_data()

    def _open_password_dialog(self) -> None:
        """Abre el diálogo para restablecer la contraseña del usuario seleccionado."""
        user = self._get_selected_user()
        if not user:
            return
        dialog = UserPasswordDialog(user=user, parent=self)
        if dialog.exec():
            self.load_data()

    def _handle_toggle_status(self) -> None:
        """Conmuta el estado activo/inactivo del usuario seleccionado."""
        user = self._get_selected_user()
        if not user or not user.id_usuario:
            return

        action_name = "desactivar" if user.activo else "activar"
        reply = QMessageBox.question(
            self,
            "Confirmar Cambio de Estado",
            f"¿Está seguro de que desea {action_name} la cuenta de @{user.username} ({user.nombre_completo})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                new_status = user_service.toggle_active_status(user.id_usuario)
                estado_txt = "activada" if new_status else "desactivada"
                QMessageBox.information(
                    self,
                    "Estado Actualizado",
                    f"La cuenta de @{user.username} ha sido {estado_txt} correctamente.",
                )
                self.load_data()
            except AppException as e:
                QMessageBox.critical(self, "Operación Denegada", e.message)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo cambiar el estado: {e}")

    def _handle_unlock(self) -> None:
        """Desbloquea la cuenta y reinicia los intentos fallidos."""
        user = self._get_selected_user()
        if not user or not user.id_usuario:
            return

        try:
            user_service.unlock_user(user.id_usuario)
            QMessageBox.information(
                self,
                "Cuenta Desbloqueada",
                f"La cuenta de @{user.username} ha sido reactivada y sus intentos fallidos reiniciados.",
            )
            self.load_data()
        except AppException as e:
            QMessageBox.critical(self, "Error", e.message)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo desbloquear la cuenta: {e}")

    def _handle_delete_user(self) -> None:
        """Elimina la cuenta seleccionada previa confirmación y verificación de dependencias."""
        user = self._get_selected_user()
        if not user or not user.id_usuario:
            return

        reply = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Está seguro de que desea ELIMINAR permanentemente la cuenta @{user.username}?\n\n"
            "Esta acción solo es permitida si el usuario no tiene historial operativo.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                user_service.delete_user(user.id_usuario)
                QMessageBox.information(
                    self,
                    "Usuario Eliminado",
                    f"La cuenta @{user.username} ha sido eliminada del sistema.",
                )
                self.load_data()
            except AppException as e:
                QMessageBox.critical(self, "No se puede eliminar", e.message)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar el usuario: {e}")
