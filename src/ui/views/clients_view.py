"""Vista principal del módulo de Catálogo de Clientes (Fase 3)."""

from typing import List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QComboBox,
)

from src.core.exceptions import AppException
from src.core.logger import get_logger
from src.domain.enums import ClientStatus
from src.domain.models import Client
from src.services.client_service import client_service
from src.ui.components.badges import get_client_status_badge
from src.ui.views.client_form_dialog import ClientFormDialog

logger = get_logger(__name__)


class ClientsView(QWidget):
    """Vista de catálogo y administración de clientes con CRUD completo."""

    # Señal emitida para retornar a la pantalla principal
    back_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._clients_cache: List[Client] = []
        self._init_ui()
        self.load_data()

    def _init_ui(self) -> None:
        """Configura los elementos de la interfaz de usuario."""
        self.setStyleSheet("background-color: #0f172a; color: #f8fafc;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(18)

        # 1. Barra Superior con Título y Navegación
        top_bar = QHBoxLayout()

        back_btn = QPushButton("← Volver al Panel")
        back_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #f8fafc;
            }
        """)
        back_btn.clicked.connect(self.back_requested.emit)
        top_bar.addWidget(back_btn)

        title_label = QLabel("Gestión y Expedientes de Clientes")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #f8fafc; margin-left: 10px;")
        top_bar.addWidget(title_label)

        top_bar.addStretch()

        self.new_client_btn = QPushButton("+ Nuevo Cliente")
        self.new_client_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        self.new_client_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_client_btn.setStyleSheet("""
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
        """)
        self.new_client_btn.clicked.connect(self._handle_new_client)
        top_bar.addWidget(self.new_client_btn)

        main_layout.addLayout(top_bar)

        # 2. Métricas y Estadísticas Rápidas (KPIs)
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(14)

        self.kpi_total = self._create_kpi_card("Total Clientes", "0", "#38bdf8")
        self.kpi_activos = self._create_kpi_card("Clientes Activos", "0", "#4ade80")
        self.kpi_morosos = self._create_kpi_card("Clientes Morosos", "0", "#fbbf24")
        self.kpi_vetados = self._create_kpi_card("Clientes Vetados", "0", "#f87171")

        kpi_layout.addWidget(self.kpi_total)
        kpi_layout.addWidget(self.kpi_activos)
        kpi_layout.addWidget(self.kpi_morosos)
        kpi_layout.addWidget(self.kpi_vetados)
        main_layout.addLayout(kpi_layout)

        # 3. Barra de Búsqueda y Filtros
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar por nombre, cédula, teléfono, email o licencia...")
        self.search_input.setFont(QFont("Segoe UI", 9))
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 14px;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
            }
        """)
        self.search_input.textChanged.connect(self._apply_filters)
        filter_bar.addWidget(self.search_input, stretch=3)

        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItem("Todos los Estados", "TODOS")
        self.status_filter_combo.addItem("Solo Activos", ClientStatus.ACTIVO.value)
        self.status_filter_combo.addItem("Solo Morosos", ClientStatus.MOROSO.value)
        self.status_filter_combo.addItem("Solo Vetados", ClientStatus.VETADO.value)
        self.status_filter_combo.setStyleSheet("""
            QComboBox {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 12px;
                min-width: 150px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                color: #f8fafc;
                selection-background-color: #0284c7;
            }
        """)
        self.status_filter_combo.currentIndexChanged.connect(self._apply_filters)
        filter_bar.addWidget(self.status_filter_combo)

        refresh_btn = QPushButton("🔄 Refrescar")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 14px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        refresh_btn.clicked.connect(self.load_data)
        filter_bar.addWidget(refresh_btn)

        main_layout.addLayout(filter_bar)

        # 4. Tabla de Clientes
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Identificación", "Tipo", "Nombre Completo", "Teléfono", "Email", "Licencia de Conducir", "Estado", "Acciones"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._handle_row_double_click)

        # Anchos predeterminados optimizados
        self.table.setColumnWidth(0, 50)    # ID
        self.table.setColumnWidth(1, 130)   # Identificación
        self.table.setColumnWidth(2, 95)    # Tipo
        # Col 3: Nombre Completo (Stretch)
        self.table.setColumnWidth(4, 115)   # Teléfono
        self.table.setColumnWidth(5, 180)   # Email
        self.table.setColumnWidth(6, 160)   # Licencia de Conducir
        self.table.setColumnWidth(7, 120)   # Estado
        self.table.setColumnWidth(8, 250)   # Acciones

        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                gridline-color: #334155;
                font-family: 'Segoe UI';
                font-size: 9pt;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #283548;
            }
            QTableWidget::item:selected {
                background-color: #24344d;
                color: #38bdf8;
            }
            QHeaderView::section {
                background-color: #0f172a;
                color: #94a3b8;
                font-weight: bold;
                border: none;
                border-bottom: 2px solid #334155;
                padding: 8px;
            }
        """)
        main_layout.addWidget(self.table, stretch=1)

    def _create_kpi_card(self, title: str, value: str, accent_color: str) -> QFrame:
        """Crea una tarjeta KPI visual moderna."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #1e293b;
                border: 1px solid #334155;
                border-left: 4px solid {accent_color};
                border-radius: 6px;
                padding: 10px 14px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Segoe UI", 8))
        lbl_title.setStyleSheet("color: #94a3b8; border: none;")

        lbl_val = QLabel(value)
        lbl_val.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_val.setStyleSheet(f"color: {accent_color}; border: none;")
        card.value_label = lbl_val  # Referencia para actualizar

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        return card

    def load_data(self) -> None:
        """Carga los clientes desde el servicio de negocio."""
        try:
            self._clients_cache = client_service.list_clients()
            self._update_kpis()
            self._render_table(self._clients_cache)
        except Exception as e:
            logger.error("Error al cargar listado de clientes: %s", e)
            QMessageBox.critical(self, "Error", f"No se pudo cargar el listado de clientes:\n{e}")

    def _update_kpis(self) -> None:
        """Actualiza las tarjetas de indicadores clave."""
        total = len(self._clients_cache)
        activos = sum(1 for c in self._clients_cache if c.estado_cliente == ClientStatus.ACTIVO)
        morosos = sum(1 for c in self._clients_cache if c.estado_cliente == ClientStatus.MOROSO)
        vetados = sum(1 for c in self._clients_cache if c.estado_cliente == ClientStatus.VETADO)

        self.kpi_total.value_label.setText(str(total))
        self.kpi_activos.value_label.setText(str(activos))
        self.kpi_morosos.value_label.setText(str(morosos))
        self.kpi_vetados.value_label.setText(str(vetados))

    def _apply_filters(self) -> None:
        """Filtra la lista según el texto de búsqueda y el combo de estado."""
        search = self.search_input.text().strip().lower()
        status_filter = self.status_filter_combo.currentData()

        filtered = []
        for c in self._clients_cache:
            if status_filter != "TODOS" and c.estado_cliente.value != status_filter:
                continue

            if search:
                lic_num = c.licencia.numero_licencia.lower() if c.licencia else ""
                match = (
                    search in c.identificacion.lower()
                    or search in c.nombres.lower()
                    or search in c.apellidos.lower()
                    or search in c.email.lower()
                    or search in c.telefono.lower()
                    or search in lic_num
                )
                if not match:
                    continue

            filtered.append(c)

        self._render_table(filtered)

    def _render_table(self, clients: List[Client]) -> None:
        """Puebla las filas de la tabla con los clientes proporcionados."""
        self.table.setRowCount(len(clients))
        self.table.setRowHeight(0, 48)

        for row_idx, c in enumerate(clients):
            self.table.setRowHeight(row_idx, 46)

            # 0. ID
            item_id = QTableWidgetItem(str(c.id_cliente))
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 0, item_id)

            # 1. Identificación
            item_ident = QTableWidgetItem(c.identificacion)
            item_ident.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            self.table.setItem(row_idx, 1, item_ident)

            # 2. Tipo Persona
            item_tipo = QTableWidgetItem("Natural" if c.tipo_persona.value == "NATURAL" else "Jurídica")
            item_tipo.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 2, item_tipo)

            # 3. Nombre Completo
            item_nombre = QTableWidgetItem(c.nombre_completo)
            self.table.setItem(row_idx, 3, item_nombre)

            # 4. Teléfono
            item_tel = QTableWidgetItem(c.telefono)
            self.table.setItem(row_idx, 4, item_tel)

            # 5. Email
            item_email = QTableWidgetItem(c.email)
            self.table.setItem(row_idx, 5, item_email)

            # 6. Licencia
            if c.licencia:
                venc_str = c.licencia.fecha_vencimiento.strftime("%d/%m/%Y") if c.licencia.fecha_vencimiento else ""
                lic_text = f"{c.licencia.numero_licencia} (Vence: {venc_str})"
            else:
                lic_text = "Sin licencia"
            item_lic = QTableWidgetItem(lic_text)
            self.table.setItem(row_idx, 6, item_lic)

            # 7. Badge de Estado
            badge_widget = QWidget()
            badge_layout = QHBoxLayout(badge_widget)
            badge_layout.setContentsMargins(4, 4, 4, 4)
            badge_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge_lbl = get_client_status_badge(c.estado_cliente)
            badge_layout.addWidget(badge_lbl)
            self.table.setCellWidget(row_idx, 7, badge_widget)

            # 8. Acciones
            actions_widget = self._create_row_actions(c)
            self.table.setCellWidget(row_idx, 8, actions_widget)

    def _create_row_actions(self, client: Client) -> QWidget:
        """Crea el contenedor de botones de acción para cada fila."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Botón Editar
        edit_btn = QPushButton("✏ Editar")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 8pt;
                font-weight: 600;
                min-height: 22px;
            }
            QPushButton:hover { background-color: #0369a1; }
        """)
        edit_btn.clicked.connect(lambda _, c=client: self._handle_edit_client(c))
        layout.addWidget(edit_btn)

        # Botón Cambiar Estado
        status_btn = QPushButton("🏷 Estado")
        status_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        status_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #e2e8f0;
                border: 1px solid #475569;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 8pt;
                font-weight: 600;
                min-height: 22px;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        status_btn.clicked.connect(lambda _, c=client: self._handle_quick_status_change(c))
        layout.addWidget(status_btn)

        # Botón Eliminar
        del_btn = QPushButton("🗑 Eliminar")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.2);
                color: #fca5a5;
                border: 1px solid rgba(239, 68, 68, 0.4);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 8pt;
                font-weight: 600;
                min-height: 22px;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: #ffffff;
            }
        """)
        del_btn.clicked.connect(lambda _, c=client: self._handle_delete_client(c))
        layout.addWidget(del_btn)

        return container

    def _handle_new_client(self) -> None:
        """Abre el diálogo modal de registro de nuevo cliente."""
        dialog = ClientFormDialog(self, client=None)
        if dialog.exec():
            self.load_data()

    def _handle_edit_client(self, client: Client) -> None:
        """Abre el diálogo modal de edición para el cliente seleccionado."""
        # Refrescar desde DB para asegurar datos frescos
        try:
            fresh_client = client_service.get_client(client.id_cliente)
            dialog = ClientFormDialog(self, client=fresh_client)
            if dialog.exec():
                self.load_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el cliente para edición: {e}")

    def _handle_row_double_click(self, row: int, column: int) -> None:
        """Doble clic en fila abre la edición del cliente."""
        item_id = self.table.item(row, 0)
        if item_id:
            c_id = int(item_id.text())
            client = next((c for c in self._clients_cache if c.id_cliente == c_id), None)
            if client:
                self._handle_edit_client(client)

    def _handle_quick_status_change(self, client: Client) -> None:
        """Permite alternar rápidamente el estado comercial del cliente."""
        statuses = [ClientStatus.ACTIVO.value, ClientStatus.MOROSO.value, ClientStatus.VETADO.value]
        current_idx = statuses.index(client.estado_cliente.value) if client.estado_cliente.value in statuses else 0
        next_status = statuses[(current_idx + 1) % len(statuses)]

        reply = QMessageBox.question(
            self,
            "Cambiar Estado",
            f"¿Desea cambiar el estado de '{client.nombre_completo}' de '{client.estado_cliente.value}' a '{next_status}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                client_service.change_status(client.id_cliente, ClientStatus(next_status))
                self.load_data()
            except AppException as e:
                QMessageBox.warning(self, "Advertencia", e.message)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al cambiar el estado: {e}")

    def _handle_delete_client(self, client: Client) -> None:
        """Solicita confirmación y ejecuta la eliminación segura del cliente."""
        reply = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Está seguro de que desea eliminar al cliente '{client.nombre_completo}' ({client.identificacion})?\n\n"
            "Nota: Si el cliente posee contratos o reservas previas, la operación será rechazada por integridad referencial.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                client_service.delete_client(client.id_cliente)
                QMessageBox.information(self, "Eliminado", f"Cliente '{client.nombre_completo}' eliminado correctamente.")
                self.load_data()
            except AppException as e:
                QMessageBox.warning(self, "Acción Bloqueada", e.message)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al eliminar cliente: {e}")
