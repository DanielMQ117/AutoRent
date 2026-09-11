"""Diálogo modal para el registro y edición de Reservas con comprobación interactiva de disponibilidad."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from PySide6.QtCore import QDateTime, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.core.exceptions import AppException
from src.core.logger import get_logger
from src.domain.enums import ClientStatus, ReservationStatus
from src.domain.models import Client, Reservation, Vehicle, VehicleCategory
from src.services.client_service import client_service
from src.services.reservation_service import reservation_service
from src.services.vehicle_service import vehicle_service

logger = get_logger(__name__)


class ReservationFormDialog(QDialog):
    """Formulario modal interactivo para crear y actualizar reservas de vehículos."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        reservation: Optional[Reservation] = None,
    ) -> None:
        super().__init__(parent)
        self.reservation = reservation
        self.is_edit_mode = reservation is not None
        self._categories: List[VehicleCategory] = []
        self._clients: List[Client] = []
        self._available_vehicles: List[Vehicle] = []

        self._init_ui()
        self._load_catalogs()

        if self.is_edit_mode:
            self._load_reservation_data()
        else:
            self._recalculate_quote()
            self._check_live_availability()

    def _init_ui(self) -> None:
        """Inicializa los componentes visuales del diálogo."""
        title = "Modificar Reserva" if self.is_edit_mode else "Nueva Reserva de Vehículo"
        self.setWindowTitle(f"AutoRent Pro — {title}")
        self.resize(700, 720)
        self.setMinimumSize(620, 640)
        self.setStyleSheet("background-color: #0f172a; color: #f8fafc;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(14)

        # 1. Cabecera
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        badge_text = "EDICIÓN" if self.is_edit_mode else "NUEVA RESERVA"
        badge_bg = "#0c4a6e" if not self.is_edit_mode else "#78350f"
        badge_color = "#38bdf8" if not self.is_edit_mode else "#fbbf24"

        badge = QLabel(f" {badge_text} ")
        badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        badge.setStyleSheet(f"""
            background-color: {badge_bg};
            color: {badge_color};
            border-radius: 4px;
            padding: 3px 8px;
        """)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #f8fafc;")

        subtitle_label = QLabel(
            "Verifique la elegibilidad del cliente, fechas de alquiler y disponibilidad antes de confirmar."
        )
        subtitle_label.setFont(QFont("Segoe UI", 9))
        subtitle_label.setStyleSheet("color: #94a3b8;")

        header_layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignLeft)
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        main_layout.addLayout(header_layout)

        # Scroll central
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        form_layout = QVBoxLayout(container)
        form_layout.setSpacing(16)
        form_layout.setContentsMargins(0, 0, 0, 0)

        # 2. Tarjeta: Selección de Cliente y Licencia
        client_card = self._create_card("1. Expediente del Cliente")
        client_grid = QGridLayout()
        client_grid.setSpacing(10)

        client_grid.addWidget(self._create_label("Cliente Arrendatario *"), 0, 0)
        self.client_combo = QComboBox()
        self.client_combo.setStyleSheet(self._combo_style())
        self.client_combo.currentIndexChanged.connect(self._on_client_changed)
        client_grid.addWidget(self.client_combo, 0, 1)

        self.client_status_label = QLabel("Seleccione un cliente para comprobar estatus.")
        self.client_status_label.setFont(QFont("Segoe UI", 8))
        self.client_status_label.setStyleSheet("color: #94a3b8;")
        client_grid.addWidget(self.client_status_label, 1, 0, 1, 2)

        client_card.layout().addLayout(client_grid)
        form_layout.addWidget(client_card)

        # 3. Tarjeta: Fechas de Alquiler y Duración
        dates_card = self._create_card("2. Período de Alquiler Solicitado")
        dates_grid = QGridLayout()
        dates_grid.setSpacing(10)

        dates_grid.addWidget(self._create_label("Fecha y Hora de Inicio *"), 0, 0)
        self.start_date_edit = QDateTimeEdit()
        self.start_date_edit.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setStyleSheet(self._input_style())
        now = datetime.now()
        self.start_date_edit.setDateTime(QDateTime(now.year, now.month, now.day, 9, 0, 0).addDays(1))
        self.start_date_edit.dateTimeChanged.connect(self._on_dates_changed)
        dates_grid.addWidget(self.start_date_edit, 0, 1)

        dates_grid.addWidget(self._create_label("Fecha y Hora de Fin *"), 1, 0)
        self.end_date_edit = QDateTimeEdit()
        self.end_date_edit.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setStyleSheet(self._input_style())
        self.end_date_edit.setDateTime(self.start_date_edit.dateTime().addDays(3))
        self.end_date_edit.dateTimeChanged.connect(self._on_dates_changed)
        dates_grid.addWidget(self.end_date_edit, 1, 1)

        dates_card.layout().addLayout(dates_grid)
        form_layout.addWidget(dates_card)

        # 4. Tarjeta: Categoría y Disponibilidad Vehicular
        vehicle_card = self._create_card("3. Categoría y Asignación de Flota")
        vehicle_grid = QGridLayout()
        vehicle_grid.setSpacing(10)

        vehicle_grid.addWidget(self._create_label("Categoría del Automóvil *"), 0, 0)
        self.category_combo = QComboBox()
        self.category_combo.setStyleSheet(self._combo_style())
        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        vehicle_grid.addWidget(self.category_combo, 0, 1)

        vehicle_grid.addWidget(self._create_label("Vehículo Específico"), 1, 0)
        self.vehicle_combo = QComboBox()
        self.vehicle_combo.setStyleSheet(self._combo_style())
        vehicle_grid.addWidget(self.vehicle_combo, 1, 1)

        # Estado visual de disponibilidad
        self.avail_badge = QLabel("✓ Comprobando disponibilidad...")
        self.avail_badge.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        self.avail_badge.setStyleSheet("color: #38bdf8; margin-top: 4px;")
        vehicle_grid.addWidget(self.avail_badge, 2, 0, 1, 2)

        vehicle_card.layout().addLayout(vehicle_grid)
        form_layout.addWidget(vehicle_card)

        # 5. Tarjeta: Cotización y Depósito de Anticipo
        cost_card = self._create_card("4. Resumen Económico y Anticipo")
        cost_grid = QGridLayout()
        cost_grid.setSpacing(10)

        self.lbl_days = QLabel("Duración: 0 días")
        self.lbl_days.setStyleSheet("color: #cbd5e1;")
        self.lbl_daily_rate = QLabel("Tarifa Base: $0.00 / día")
        self.lbl_daily_rate.setStyleSheet("color: #cbd5e1;")
        self.lbl_total_cost = QLabel("Costo Estimado: $0.00")
        self.lbl_total_cost.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_total_cost.setStyleSheet("color: #38bdf8;")

        cost_grid.addWidget(self.lbl_days, 0, 0)
        cost_grid.addWidget(self.lbl_daily_rate, 0, 1)
        cost_grid.addWidget(self.lbl_total_cost, 1, 0, 1, 2)

        cost_grid.addWidget(self._create_label("Monto de Anticipo ($)"), 2, 0)
        self.anticipo_spin = QDoubleSpinBox()
        self.anticipo_spin.setRange(0.00, 99999.00)
        self.anticipo_spin.setDecimals(2)
        self.anticipo_spin.setPrefix("$ ")
        self.anticipo_spin.setStyleSheet(self._input_style())
        cost_grid.addWidget(self.anticipo_spin, 2, 1)

        cost_card.layout().addLayout(cost_grid)
        form_layout.addWidget(cost_card)

        scroll_area.setWidget(container)
        main_layout.addWidget(scroll_area, stretch=1)

        # 6. Botones de Acción
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setFont(QFont("Segoe UI", 9))
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #e2e8f0;
                border: none;
                border-radius: 6px;
                padding: 10px 18px;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)
        cancel_btn.clicked.connect(self.reject)

        self.save_btn = QPushButton("Confirmar y Guardar Reserva")
        self.save_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 10px 22px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        self.save_btn.clicked.connect(self._handle_save)

        actions_layout.addStretch()
        actions_layout.addWidget(cancel_btn)
        actions_layout.addWidget(self.save_btn)
        main_layout.addLayout(actions_layout)

    def _create_card(self, title: str) -> QFrame:
        """Genera un contenedor estilizado de tarjeta para agrupar campos."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 14px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        card_title = QLabel(title)
        card_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        card_title.setStyleSheet("color: #f1f5f9; border: none;")
        layout.addWidget(card_title)
        return card

    @staticmethod
    def _create_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        lbl.setStyleSheet("color: #cbd5e1; border: none;")
        return lbl

    @staticmethod
    def _input_style() -> str:
        return """
            QLineEdit, QDateTimeEdit, QDoubleSpinBox {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 10px;
            }
            QLineEdit:focus, QDateTimeEdit:focus, QDoubleSpinBox:focus {
                border: 1px solid #38bdf8;
            }
        """

    @staticmethod
    def _combo_style() -> str:
        return """
            QComboBox {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 10px;
            }
            QComboBox:focus {
                border: 1px solid #38bdf8;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                color: #f8fafc;
                selection-background-color: #0284c7;
                border: 1px solid #334155;
            }
        """

    def _load_catalogs(self) -> None:
        """Carga los catálogos de Clientes y Categorías de vehículos."""
        try:
            # Clientes activos
            self._clients = client_service.list_clients(status="ACTIVO")
            self.client_combo.clear()
            for c in self._clients:
                ident = c.identificacion
                lic_str = f" [Lic: {c.licencia.numero_licencia}]" if c.licencia else " [Sin Licencia]"
                self.client_combo.addItem(f"{c.nombre_completo} ({ident}){lic_str}", c.id_cliente)

            # Categorías de Vehículos
            self._categories = vehicle_service.get_categories()
            self.category_combo.clear()
            for cat in self._categories:
                self.category_combo.addItem(f"{cat.nombre} — ${cat.tarifa_base_diaria}/día", cat.id_categoria)

        except Exception as e:
            logger.error("Error al cargar catálogos en ReservationFormDialog: %s", e)

    def _on_client_changed(self) -> None:
        """Verifica la licencia del cliente seleccionado en tiempo real."""
        idx = self.client_combo.currentIndex()
        if idx < 0 or idx >= len(self._clients):
            return

        client = self._clients[idx]
        end_dt = self.end_date_edit.dateTime().toPython()

        if client.licencia:
            exp_date = client.licencia.fecha_vencimiento
            if exp_date < end_dt.date():
                self.client_status_label.setText(
                    f"⚠ Advertencia: La licencia vence el {exp_date.strftime('%d/%m/%Y')} (antes de la entrega)."
                )
                self.client_status_label.setStyleSheet("color: #f87171; font-weight: bold;")
            else:
                self.client_status_label.setText(
                    f"✓ Licencia válida hasta: {exp_date.strftime('%d/%m/%Y')} ({client.licencia.categoria_licencia})."
                )
                self.client_status_label.setStyleSheet("color: #4ade80;")
        else:
            self.client_status_label.setText("⛔ Cliente sin licencia de conducir registrada.")
            self.client_status_label.setStyleSheet("color: #f87171; font-weight: bold;")

    def _on_dates_changed(self) -> None:
        """Reacciona al cambio de fechas recalculando cotización y disponibilidad."""
        self._recalculate_quote()
        self._check_live_availability()
        self._on_client_changed()

    def _on_category_changed(self) -> None:
        """Reacciona al cambio de categoría de vehículo."""
        self._recalculate_quote()
        self._check_live_availability()

    def _recalculate_quote(self) -> None:
        """Calcula días, tarifa y total proyectado de la reserva."""
        start_dt = self.start_date_edit.dateTime().toPython()
        end_dt = self.end_date_edit.dateTime().toPython()
        cat_id = self.category_combo.currentData()

        if not cat_id or end_dt <= start_dt:
            self.lbl_days.setText("Duración: 0 días")
            self.lbl_total_cost.setText("Costo Estimado: $0.00")
            return

        try:
            dias, tarifa, total = reservation_service.calculate_duration_and_cost(
                id_categoria=cat_id,
                start_dt=start_dt,
                end_dt=end_dt,
            )
            self.lbl_days.setText(f"Duración: {dias} día(s)")
            self.lbl_daily_rate.setText(f"Tarifa Base: ${tarifa:.2f} / día")
            self.lbl_total_cost.setText(f"Costo Estimado: ${total:.2f}")

            # Sugerir anticipo del 20% si es nueva reserva y el campo está en 0
            if not self.is_edit_mode and self.anticipo_spin.value() == 0.0:
                sugerido = float(total * Decimal("0.20"))
                self.anticipo_spin.setValue(sugerido)

        except Exception as e:
            logger.debug("Recálculo omitido por fecha incompleta: %s", e)

    def _check_live_availability(self) -> None:
        """Consulta vehículos libres para el período y categoría seleccionados."""
        cat_id = self.category_combo.currentData()
        start_dt = self.start_date_edit.dateTime().toPython()
        end_dt = self.end_date_edit.dateTime().toPython()

        if not cat_id or end_dt <= start_dt:
            self.avail_badge.setText("Ingrese un rango de fechas válido.")
            self.avail_badge.setStyleSheet("color: #fbbf24;")
            return

        exclude_id = self.reservation.id_reserva if self.is_edit_mode and self.reservation else None

        is_avail, vehicles, msg = reservation_service.check_availability(
            id_categoria=cat_id,
            start_dt=start_dt,
            end_dt=end_dt,
            exclude_reservation_id=exclude_id,
        )

        self.vehicle_combo.clear()
        self.vehicle_combo.addItem("-- Asignar en Contrato (Cualquier vehículo libre) --", None)

        if is_avail:
            self.avail_badge.setText(f"✓ {msg}")
            self.avail_badge.setStyleSheet("color: #4ade80; font-weight: bold;")
            for v in vehicles:
                self.vehicle_combo.addItem(f"{v.placa} — {v.modelo_nombre} ({v.color})", v.id_vehiculo)
        else:
            self.avail_badge.setText(f"⛔ {msg}")
            self.avail_badge.setStyleSheet("color: #f87171; font-weight: bold;")

    def _load_reservation_data(self) -> None:
        """Carga los datos en modo edición."""
        if not self.reservation:
            return

        r = self.reservation
        # Seleccionar cliente
        idx_cli = self.client_combo.findData(r.id_cliente)
        if idx_cli >= 0:
            self.client_combo.setCurrentIndex(idx_cli)

        # Seleccionar categoría
        idx_cat = self.category_combo.findData(r.id_categoria)
        if idx_cat >= 0:
            self.category_combo.setCurrentIndex(idx_cat)

        if r.fecha_hora_inicio:
            self.start_date_edit.setDateTime(QDateTime(r.fecha_hora_inicio))
        if r.fecha_hora_fin:
            self.end_date_edit.setDateTime(QDateTime(r.fecha_hora_fin))

        self.anticipo_spin.setValue(float(r.monto_anticipo))

        self._recalculate_quote()
        self._check_live_availability()

        if r.id_vehiculo:
            idx_v = self.vehicle_combo.findData(r.id_vehiculo)
            if idx_v >= 0:
                self.vehicle_combo.setCurrentIndex(idx_v)

    def _handle_save(self) -> None:
        """Valida y guarda la reserva mediante el servicio empresarial."""
        client_id = self.client_combo.currentData()
        cat_id = self.category_combo.currentData()
        veh_id = self.vehicle_combo.currentData()
        start_dt = self.start_date_edit.dateTime().toPython()
        end_dt = self.end_date_edit.dateTime().toPython()
        anticipo = Decimal(str(self.anticipo_spin.value()))

        if not client_id:
            QMessageBox.warning(self, "Campo Requerido", "Debe seleccionar un cliente.")
            return

        if not cat_id:
            QMessageBox.warning(self, "Campo Requerido", "Debe seleccionar una categoría de vehículo.")
            return

        res = self.reservation or Reservation()
        res.id_cliente = client_id
        res.id_categoria = cat_id
        res.id_vehiculo = veh_id
        res.fecha_hora_inicio = start_dt
        res.fecha_hora_fin = end_dt
        res.monto_anticipo = anticipo

        try:
            if self.is_edit_mode:
                reservation_service.update_reservation(res)
                QMessageBox.information(self, "Éxito", "Reserva actualizada satisfactoriamente.")
            else:
                created = reservation_service.create_reservation(res)
                QMessageBox.information(
                    self,
                    "Reserva Registrada",
                    f"Reserva registrada con éxito.\n\n"
                    f"Código Asignado: {created.codigo_reserva}\n"
                    f"Estado: {created.estado.value}\n"
                    f"Anticipo Registrado: ${created.monto_anticipo:.2f}",
                )

            self.accept()

        except AppException as e:
            QMessageBox.warning(self, "Validación de Reserva", e.message)
        except Exception as e:
            logger.error("Error al guardar reserva: %s", e)
            QMessageBox.critical(self, "Error Inesperado", f"Ocurrió un error al persistir la reserva:\n{e}")
