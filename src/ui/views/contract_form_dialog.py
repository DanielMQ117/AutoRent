"""Diálogo interactivo para emisión, formalización e inspección de entrega de contratos (UI)."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from PySide6.QtCore import QDate, QDateTime, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.exceptions import AppException
from src.core.logger import get_logger
from src.domain.enums import ClientStatus, PaymentMethod, VehicleStatus
from src.domain.models import (
    AdditionalDriver,
    Client,
    Contract,
    InsuranceCoverage,
    Reservation,
    Vehicle,
)
from src.services.client_service import client_service
from src.services.contract_service import contract_service
from src.services.vehicle_service import vehicle_service

logger = get_logger(__name__)


class ContractFormDialog(QDialog):
    """Diálogo modal para crear contratos directos o formalizar reservas con entrega física."""

    def __init__(
        self,
        contract: Optional[Contract] = None,
        reservation: Optional[Reservation] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.contract = contract
        self.reservation = reservation
        self.is_view_mode = contract is not None
        self.is_from_reservation = reservation is not None

        self._clients: List[Client] = []
        self._vehicles: List[Vehicle] = []
        self._coverages: List[InsuranceCoverage] = []
        self._additional_drivers: List[AdditionalDriver] = []

        self._init_ui()
        self._load_catalogs()

        if self.is_view_mode and self.contract:
            self._load_contract_data()
        elif self.is_from_reservation and self.reservation:
            self._load_reservation_data()
        else:
            self._recalculate_quote()

    def _init_ui(self) -> None:
        """Configura la estructura visual del formulario."""
        if self.is_view_mode:
            title = f"Detalle de Contrato — {self.contract.codigo_contrato if self.contract else ''}"
        elif self.is_from_reservation:
            title = f"Formalizar Reserva — {self.reservation.codigo_reserva if self.reservation else ''}"
        else:
            title = "Apertura de Contrato y Entrega de Vehículo"

        self.setWindowTitle(f"AutoRent Pro — {title}")
        self.resize(880, 840)
        self.setMinimumSize(800, 740)
        self.setStyleSheet("background-color: #0f172a; color: #f8fafc;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(12)

        # 1. Cabecera
        header = QVBoxLayout()
        header.setSpacing(2)

        tag_text = "CONSULTA" if self.is_view_mode else ("DESDE RESERVA" if self.is_from_reservation else "CONTRATO DIRECTO")
        badge = QLabel(f"  {tag_text}  ")
        badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        badge.setStyleSheet("""
            background-color: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 4px;
            padding: 2px 8px;
        """)
        header.addWidget(badge, alignment=Qt.AlignmentFlag.AlignLeft)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #f8fafc;")
        header.addWidget(title_lbl)

        sub_lbl = QLabel("Registro del contrato de arrendamiento, entrega física del vehículo y control de garantías.")
        sub_lbl.setFont(QFont("Segoe UI", 9))
        sub_lbl.setStyleSheet("color: #94a3b8;")
        header.addWidget(sub_lbl)

        main_layout.addLayout(header)

        # 2. Scroll Area con Secciones
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        form_layout = QVBoxLayout(container)
        form_layout.setSpacing(14)
        form_layout.setContentsMargins(0, 0, 10, 0)

        # --- SECCIÓN 1: CLIENTE ARRENDATARIO ---
        client_card = self._create_card("1. Expediente del Cliente")
        client_grid = QGridLayout()
        client_grid.setSpacing(10)
        client_grid.setColumnStretch(0, 0)
        client_grid.setColumnStretch(1, 1)

        client_grid.addWidget(self._create_label("Cliente Registrado *"), 0, 0)
        self.client_combo = QComboBox()
        self.client_combo.setFont(QFont("Segoe UI", 9))
        self.client_combo.setStyleSheet(self._input_style())
        self.client_combo.currentIndexChanged.connect(self._on_client_changed)
        client_grid.addWidget(self.client_combo, 0, 1)

        self.client_info_lbl = QLabel("Seleccione un cliente para comprobar licencia...")
        self.client_info_lbl.setFont(QFont("Segoe UI", 8))
        self.client_info_lbl.setStyleSheet("color: #94a3b8;")
        client_grid.addWidget(self.client_info_lbl, 1, 0, 1, 2)

        client_card.layout().addLayout(client_grid)
        form_layout.addWidget(client_card)

        # --- SECCIÓN 2: VEHÍCULO & INSPECCIÓN DE SALIDA ---
        veh_card = self._create_card("2. Vehículo y Entrega de Flota")
        veh_grid = QGridLayout()
        veh_grid.setSpacing(10)
        veh_grid.setColumnStretch(0, 0)
        veh_grid.setColumnStretch(1, 1)

        veh_grid.addWidget(self._create_label("Vehículo Asignado *"), 0, 0)
        self.vehicle_combo = QComboBox()
        self.vehicle_combo.setFont(QFont("Segoe UI", 9))
        self.vehicle_combo.setStyleSheet(self._input_style())
        self.vehicle_combo.currentIndexChanged.connect(self._on_vehicle_changed)
        veh_grid.addWidget(self.vehicle_combo, 0, 1)

        veh_grid.addWidget(self._create_label("Kilometraje de Salida *"), 1, 0)
        self.km_salida_spin = QSpinBox()
        self.km_salida_spin.setRange(0, 999999)
        self.km_salida_spin.setStyleSheet(self._input_style())
        veh_grid.addWidget(self.km_salida_spin, 1, 1)

        veh_grid.addWidget(self._create_label("Nivel de Combustible *"), 2, 0)
        self.fuel_combo = QComboBox()
        self.fuel_combo.setFont(QFont("Segoe UI", 9))
        self.fuel_combo.setStyleSheet(self._input_style())
        self.fuel_combo.addItem("1.00 — Tanque Lleno (100%)", Decimal("1.00"))
        self.fuel_combo.addItem("0.75 — Tres Cuartos (75%)", Decimal("0.75"))
        self.fuel_combo.addItem("0.50 — Medio Tanque (50%)", Decimal("0.50"))
        self.fuel_combo.addItem("0.25 — Un Cuarto (25%)", Decimal("0.25"))
        veh_grid.addWidget(self.fuel_combo, 2, 1)

        # Checklist de inventario físico
        checklist_box = QFrame()
        checklist_box.setStyleSheet("background-color: #0f172a; border-radius: 6px; padding: 6px;")
        chk_layout = QGridLayout(checklist_box)
        self.chk_llave = QCheckBox("Llave de Encendido y Repuesto")
        self.chk_llave.setChecked(True)
        self.chk_llanta = QCheckBox("Llanta de Auxilio en buen estado")
        self.chk_llanta.setChecked(True)
        self.chk_gata = QCheckBox("Gata Hidráulica y Llave de Ruedas")
        self.chk_gata.setChecked(True)
        self.chk_docs = QCheckBox("Circulación y Seguro Obligatorio")
        self.chk_docs.setChecked(True)

        for w in (self.chk_llave, self.chk_llanta, self.chk_gata, self.chk_docs):
            w.setStyleSheet("color: #cbd5e1; font-size: 8pt;")

        chk_layout.addWidget(self.chk_llave, 0, 0)
        chk_layout.addWidget(self.chk_llanta, 0, 1)
        chk_layout.addWidget(self.chk_gata, 1, 0)
        chk_layout.addWidget(self.chk_docs, 1, 1)

        veh_grid.addWidget(self._create_label("Inventario Físico de Entrega"), 3, 0)
        veh_grid.addWidget(checklist_box, 3, 1)

        veh_card.layout().addLayout(veh_grid)
        form_layout.addWidget(veh_card)

        # --- SECCIÓN 3: VIGENCIA PACTADA ---
        dates_card = self._create_card("3. Vigencia y Fechas del Alquiler")
        dates_grid = QGridLayout()
        dates_grid.setSpacing(10)
        dates_grid.setColumnStretch(0, 0)
        dates_grid.setColumnStretch(1, 1)

        dates_grid.addWidget(self._create_label("Inicio Pactado *"), 0, 0)
        self.start_date_edit = QDateTimeEdit()
        self.start_date_edit.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setStyleSheet(self._input_style())
        now = datetime.now()
        self.start_date_edit.setDateTime(QDateTime(now.year, now.month, now.day, now.hour, now.minute, 0))
        self.start_date_edit.dateTimeChanged.connect(self._recalculate_quote)
        dates_grid.addWidget(self.start_date_edit, 0, 1)

        dates_grid.addWidget(self._create_label("Fin Pactado *"), 1, 0)
        self.end_date_edit = QDateTimeEdit()
        self.end_date_edit.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setStyleSheet(self._input_style())
        self.end_date_edit.setDateTime(self.start_date_edit.dateTime().addDays(3))
        self.end_date_edit.dateTimeChanged.connect(self._recalculate_quote)
        dates_grid.addWidget(self.end_date_edit, 1, 1)

        dates_card.layout().addLayout(dates_grid)
        form_layout.addWidget(dates_card)

        # --- SECCIÓN 4: COBERTURA, TARIFAS Y GARANTÍA ---
        cost_card = self._create_card("4. Seguro, Tarifas y Garantía")
        cost_grid = QGridLayout()
        cost_grid.setSpacing(10)
        cost_grid.setColumnStretch(0, 0)
        cost_grid.setColumnStretch(1, 1)

        cost_grid.addWidget(self._create_label("Póliza de Cobertura *"), 0, 0)
        self.coverage_combo = QComboBox()
        self.coverage_combo.setFont(QFont("Segoe UI", 9))
        self.coverage_combo.setStyleSheet(self._input_style())
        self.coverage_combo.currentIndexChanged.connect(self._recalculate_quote)
        cost_grid.addWidget(self.coverage_combo, 0, 1)

        cost_grid.addWidget(self._create_label("Tarifa Diaria Aplicada ($) *"), 1, 0)
        self.tarifa_spin = QDoubleSpinBox()
        self.tarifa_spin.setRange(5.0, 2000.0)
        self.tarifa_spin.setDecimals(2)
        self.tarifa_spin.setPrefix("$ ")
        self.tarifa_spin.setStyleSheet(self._input_style())
        self.tarifa_spin.valueChanged.connect(self._recalculate_quote)
        cost_grid.addWidget(self.tarifa_spin, 1, 1)

        cost_grid.addWidget(self._create_label("Depósito en Garantía ($) *"), 2, 0)
        self.garantia_spin = QDoubleSpinBox()
        self.garantia_spin.setRange(0.0, 10000.0)
        self.garantia_spin.setDecimals(2)
        self.garantia_spin.setPrefix("$ ")
        self.garantia_spin.setStyleSheet(self._input_style())
        cost_grid.addWidget(self.garantia_spin, 2, 1)

        cost_grid.addWidget(self._create_label("Método Pago de Garantía *"), 3, 0)
        self.metodo_combo = QComboBox()
        self.metodo_combo.setFont(QFont("Segoe UI", 9))
        self.metodo_combo.setStyleSheet(self._input_style())
        for m in PaymentMethod:
            self.metodo_combo.addItem(m.value.replace("_", " ").title(), m)
        cost_grid.addWidget(self.metodo_combo, 3, 1)

        cost_grid.addWidget(self._create_label("Referencia / Voucher"), 4, 0)
        self.referencia_input = QLineEdit()
        self.referencia_input.setPlaceholderText("Ej: AUT-984321 / Efectivo en caja")
        self.referencia_input.setStyleSheet(self._input_style())
        cost_grid.addWidget(self.referencia_input, 4, 1)

        cost_card.layout().addLayout(cost_grid)
        form_layout.addWidget(cost_card)

        # --- SECCIÓN 5: CONDUCTORES ADICIONALES ---
        driver_card = self._create_card("5. Conductores Adicionales (Opcional)")
        driver_card_layout = QVBoxLayout()
        driver_card_layout.setSpacing(8)

        driver_btn_bar = QHBoxLayout()
        driver_info = QLabel("Puede registrar conductores facultados para operar el vehículo durante el contrato.")
        driver_info.setFont(QFont("Segoe UI", 8))
        driver_info.setStyleSheet("color: #94a3b8;")
        driver_btn_bar.addWidget(driver_info)
        driver_btn_bar.addStretch()

        if not self.is_view_mode:
            add_driver_btn = QPushButton("＋ Agregar Conductor")
            add_driver_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
            add_driver_btn.setStyleSheet("""
                QPushButton {
                    background-color: #334155;
                    color: #38bdf8;
                    border: 1px solid #38bdf8;
                    border-radius: 4px;
                    padding: 4px 10px;
                }
                QPushButton:hover {
                    background-color: #0284c7;
                    color: #ffffff;
                }
            """)
            add_driver_btn.clicked.connect(self._add_driver_row)
            driver_btn_bar.addWidget(add_driver_btn)

        driver_card_layout.addLayout(driver_btn_bar)

        self.drivers_table = QTableWidget(0, 4)
        self.drivers_table.setHorizontalHeaderLabels(["Nombre Completo", "Identificación", "Nº Licencia", "Vencimiento (YYYY-MM-DD)"])
        self.drivers_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.drivers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.drivers_table.horizontalHeader().setStretchLastSection(False)
        self.drivers_table.verticalHeader().setVisible(False)
        self.drivers_table.verticalHeader().setDefaultSectionSize(38)
        self.drivers_table.setColumnWidth(1, 140)
        self.drivers_table.setColumnWidth(2, 140)
        self.drivers_table.setColumnWidth(3, 160)
        self.drivers_table.setFixedHeight(140)
        self.drivers_table.setStyleSheet("""
            QTableWidget {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #f8fafc;
            }
            QHeaderView::section {
                background-color: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                font-size: 8pt;
                font-weight: bold;
                padding: 6px;
            }
        """)
        driver_card_layout.addWidget(self.drivers_table)
        driver_card.layout().addLayout(driver_card_layout)
        form_layout.addWidget(driver_card)

        # --- SECCIÓN 6: RESUMEN ECONÓMICO ---
        self.summary_card = QFrame()
        self.summary_card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #38bdf8;
                border-radius: 8px;
            }
        """)
        summary_layout = QHBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(16, 12, 16, 12)

        self.summary_days_lbl = QLabel("Días: 0")
        self.summary_days_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.summary_days_lbl.setStyleSheet("color: #38bdf8;")

        self.summary_subtotal_lbl = QLabel("Subtotal Renta: $0.00")
        self.summary_subtotal_lbl.setFont(QFont("Segoe UI", 9))
        self.summary_subtotal_lbl.setStyleSheet("color: #cbd5e1;")

        self.summary_seguro_lbl = QLabel("Seguro: $0.00")
        self.summary_seguro_lbl.setFont(QFont("Segoe UI", 9))
        self.summary_seguro_lbl.setStyleSheet("color: #cbd5e1;")

        self.summary_anticipo_lbl = QLabel("Anticipo: -$0.00")
        self.summary_anticipo_lbl.setFont(QFont("Segoe UI", 9))
        self.summary_anticipo_lbl.setStyleSheet("color: #34d399;")

        self.summary_total_lbl = QLabel("Total a Cobrar: $0.00")
        self.summary_total_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.summary_total_lbl.setStyleSheet("color: #38bdf8;")

        summary_layout.addWidget(self.summary_days_lbl)
        summary_layout.addWidget(self.summary_subtotal_lbl)
        summary_layout.addWidget(self.summary_seguro_lbl)
        summary_layout.addWidget(self.summary_anticipo_lbl)
        summary_layout.addStretch()
        summary_layout.addWidget(self.summary_total_lbl)

        form_layout.addWidget(self.summary_card)

        scroll.setWidget(container)
        main_layout.addWidget(scroll, stretch=1)

        # 3. Barra de Botones Inferior
        actions_bar = QHBoxLayout()
        actions_bar.addStretch()

        cancel_btn = QPushButton("Cerrar" if self.is_view_mode else "Cancelar")
        cancel_btn.setFont(QFont("Segoe UI", 9))
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #e2e8f0;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 8px 18px;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        cancel_btn.clicked.connect(self.reject)
        actions_bar.addWidget(cancel_btn)

        if not self.is_view_mode:
            self.save_btn = QPushButton("Emitir Contrato y Entregar Llaves 🚗")
            self.save_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0284c7;
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 20px;
                }
                QPushButton:hover { background-color: #0369a1; }
            """)
            self.save_btn.clicked.connect(self._save_contract)
            actions_bar.addWidget(self.save_btn)

        main_layout.addLayout(actions_bar)

    def _create_card(self, title_text: str) -> QFrame:
        """Crea una tarjeta contenedora estilizada para agrupar campos."""
        card = QFrame(self)
        card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(18, 16, 18, 16)

        header = QLabel(title_text)
        header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        header.setStyleSheet("color: #38bdf8; border: none;")
        card_layout.addWidget(header)
        return card

    @staticmethod
    def _create_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet("color: #cbd5e1; border: none;")
        return lbl

    @staticmethod
    def _input_style() -> str:
        return """
            QLineEdit, QComboBox, QDateTimeEdit, QSpinBox, QDoubleSpinBox {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
            }
            QLineEdit:focus, QComboBox:focus, QDateTimeEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #38bdf8;
            }
        """

    def _load_catalogs(self) -> None:
        """Carga clientes, vehículos disponibles y coberturas de seguro."""
        try:
            self._clients = client_service.list_clients(status=ClientStatus.ACTIVO.value)
            self.client_combo.clear()
            self.client_combo.addItem("-- Seleccione Cliente --", None)
            for c in self._clients:
                self.client_combo.addItem(f"{c.nombre_completo} ({c.identificacion})", c.id_cliente)

            # Vehículos disponibles o todos si es modo consulta
            if self.is_view_mode:
                self._vehicles = vehicle_service.list_vehicles()
            else:
                self._vehicles = vehicle_service.list_vehicles(status=VehicleStatus.DISPONIBLE.value)

            self.vehicle_combo.clear()
            self.vehicle_combo.addItem("-- Seleccione Vehículo --", None)
            for v in self._vehicles:
                self.vehicle_combo.addItem(f"{v.placa} — {v.marca_nombre} {v.modelo_nombre} ({v.categoria_nombre})", v.id_vehiculo)

            # Coberturas de seguro
            self._coverages = contract_service.get_coverages()
            self.coverage_combo.clear()
            for cob in self._coverages:
                self.coverage_combo.addItem(f"{cob.nombre} — ${cob.costo_diario}/día (Deducible: {cob.porcentaje_deducible}%)", cob.id_cobertura)

        except Exception as e:
            logger.error("Error al cargar catálogos en ContractFormDialog: %s", e)
            QMessageBox.critical(self, "Error de Conexión", f"No se pudieron cargar los catálogos: {e}")

    def _on_client_changed(self) -> None:
        """Actualiza la información de licencia del cliente seleccionado."""
        client_id = self.client_combo.currentData()
        if not client_id:
            self.client_info_lbl.setText("Seleccione un cliente para comprobar licencia...")
            self.client_info_lbl.setStyleSheet("color: #94a3b8;")
            return

        client = next((c for c in self._clients if c.id_cliente == client_id), None)
        if not client:
            return

        if client.licencia:
            venc_str = client.licencia.fecha_vencimiento.strftime("%d/%m/%Y")
            if client.licencia.fecha_vencimiento < date.today():
                self.client_info_lbl.setText(f"⚠ LICENCIA VENCIDA el {venc_str} ({client.licencia.numero_licencia})")
                self.client_info_lbl.setStyleSheet("color: #f87171; font-weight: bold;")
            else:
                self.client_info_lbl.setText(f"✓ Licencia {client.licencia.numero_licencia} — Vence: {venc_str} ({client.licencia.categoria_licencia})")
                self.client_info_lbl.setStyleSheet("color: #34d399;")
        else:
            self.client_info_lbl.setText("⚠ Cliente sin licencia de conducir registrada.")
            self.client_info_lbl.setStyleSheet("color: #f87171; font-weight: bold;")

    def _on_vehicle_changed(self) -> None:
        """Actualiza odómetro y tarifa sugerida según el vehículo seleccionado."""
        veh_id = self.vehicle_combo.currentData()
        if not veh_id:
            return

        vehicle = next((v for v in self._vehicles if v.id_vehiculo == veh_id), None)
        if not vehicle:
            return

        self.km_salida_spin.setValue(vehicle.kilometraje_actual)
        self.km_salida_spin.setMinimum(vehicle.kilometraje_actual)

        # Buscar categoría y fijar tarifa base y depósito sugerido
        categories = vehicle_service.get_categories()
        category = next((c for c in categories if c.id_categoria == vehicle.id_categoria), None)
        if category:
            self.tarifa_spin.setValue(float(category.tarifa_base_diaria))
            self.garantia_spin.setValue(float(category.deposito_garantia_sugerido))

        self._recalculate_quote()

    def _recalculate_quote(self) -> None:
        """Calcula el desglose económico de renta, seguro, anticipo y saldo en mostrador."""
        start_py = self.start_date_edit.dateTime().toPython()
        end_py = self.end_date_edit.dateTime().toPython()

        if end_py <= start_py:
            self.summary_days_lbl.setText("Días: Inválido")
            self.summary_total_lbl.setText("Total: Incoherente")
            return

        delta = end_py - start_py
        dias = delta.days
        if delta.seconds > 3600:
            dias += 1
        dias = max(1, dias)

        tarifa = Decimal(str(self.tarifa_spin.value()))
        subtotal_renta = tarifa * Decimal(dias)

        coverage_id = self.coverage_combo.currentData()
        coverage = next((c for c in self._coverages if c.id_cobertura == coverage_id), None)
        seguro_total = (coverage.costo_diario * Decimal(dias)) if coverage else Decimal("0.00")

        anticipo = self.reservation.monto_anticipo if (self.is_from_reservation and self.reservation) else Decimal("0.00")
        garantia = Decimal(str(self.garantia_spin.value()))

        # Total a pagar en mostrador al retirar el vehículo = renta + seguro + garantía - anticipo previo
        total_mostrador = max(Decimal("0.00"), subtotal_renta + seguro_total + garantia - anticipo)

        self.summary_days_lbl.setText(f"Días: {dias}")
        self.summary_subtotal_lbl.setText(f"Renta: ${subtotal_renta:.2f}")
        self.summary_seguro_lbl.setText(f"Seguro: ${seguro_total:.2f}")
        self.summary_anticipo_lbl.setText(f"Anticipo: -${anticipo:.2f}")
        self.summary_total_lbl.setText(f"Total en Mostrador: ${total_mostrador:.2f}")

    def _add_driver_row(self) -> None:
        """Inserta una nueva fila en la tabla de conductores adicionales."""
        row_pos = self.drivers_table.rowCount()
        self.drivers_table.insertRow(row_pos)
        self.drivers_table.setItem(row_pos, 0, QTableWidgetItem(""))
        self.drivers_table.setItem(row_pos, 1, QTableWidgetItem(""))
        self.drivers_table.setItem(row_pos, 2, QTableWidgetItem(""))
        default_exp = (date.today() + timedelta(days=365)).strftime("%Y-%m-%d")
        self.drivers_table.setItem(row_pos, 3, QTableWidgetItem(default_exp))

    def _load_reservation_data(self) -> None:
        """Precarga los datos provenientes de la reserva seleccionada para formalizar."""
        if not self.reservation:
            return

        r = self.reservation
        # Seleccionar cliente
        idx = self.client_combo.findData(r.id_cliente)
        if idx >= 0:
            self.client_combo.setCurrentIndex(idx)
        self.client_combo.setEnabled(False)

        # Si la reserva tenía vehículo asignado, seleccionarlo
        if r.id_vehiculo:
            # Asegurar que esté en el combo aunque su estado sea RESERVADO
            veh = vehicle_service.get_vehicle(r.id_vehiculo)
            if veh and self.vehicle_combo.findData(r.id_vehiculo) < 0:
                self.vehicle_combo.addItem(f"{veh.placa} — {veh.marca_nombre} {veh.modelo_nombre} (Asignado)", veh.id_vehiculo)
            v_idx = self.vehicle_combo.findData(r.id_vehiculo)
            if v_idx >= 0:
                self.vehicle_combo.setCurrentIndex(v_idx)

        # Fechas
        if r.fecha_hora_inicio:
            self.start_date_edit.setDateTime(QDateTime(r.fecha_hora_inicio))
        if r.fecha_hora_fin:
            self.end_date_edit.setDateTime(QDateTime(r.fecha_hora_fin))

        self._recalculate_quote()

    def _load_contract_data(self) -> None:
        """Carga en modo sólo lectura el detalle de un contrato existente."""
        if not self.contract:
            return

        c = self.contract
        self.client_combo.addItem(f"{c.cliente_nombre} ({c.cliente_identificacion})", c.id_cliente)
        self.client_combo.setCurrentIndex(self.client_combo.count() - 1)
        self.client_combo.setEnabled(False)

        self.vehicle_combo.addItem(f"{c.vehiculo_placa} — {c.vehiculo_modelo}", c.id_vehiculo)
        self.vehicle_combo.setCurrentIndex(self.vehicle_combo.count() - 1)
        self.vehicle_combo.setEnabled(False)

        self.km_salida_spin.setValue(c.kilometraje_salida)
        self.km_salida_spin.setEnabled(False)

        fuel_idx = self.fuel_combo.findData(c.combustible_salida)
        if fuel_idx >= 0:
            self.fuel_combo.setCurrentIndex(fuel_idx)
        self.fuel_combo.setEnabled(False)

        if c.fecha_hora_inicio_pactada:
            self.start_date_edit.setDateTime(QDateTime(c.fecha_hora_inicio_pactada))
        if c.fecha_hora_fin_pactada:
            self.end_date_edit.setDateTime(QDateTime(c.fecha_hora_fin_pactada))
        self.start_date_edit.setEnabled(False)
        self.end_date_edit.setEnabled(False)

        cov_idx = self.coverage_combo.findData(c.id_cobertura)
        if cov_idx >= 0:
            self.coverage_combo.setCurrentIndex(cov_idx)
        self.coverage_combo.setEnabled(False)

        self.tarifa_spin.setValue(float(c.tarifa_diaria_aplicada))
        self.tarifa_spin.setEnabled(False)

        self.garantia_spin.setValue(float(c.monto_garantia))
        self.garantia_spin.setEnabled(False)

        self.metodo_combo.setEnabled(False)
        self.referencia_input.setEnabled(False)

        # Cargar conductores adicionales
        self.drivers_table.setRowCount(0)
        for d in c.conductores_adicionales:
            r = self.drivers_table.rowCount()
            self.drivers_table.insertRow(r)
            self.drivers_table.setItem(r, 0, QTableWidgetItem(d.nombre_completo))
            self.drivers_table.setItem(r, 1, QTableWidgetItem(d.identificacion))
            self.drivers_table.setItem(r, 2, QTableWidgetItem(d.numero_licencia))
            v_str = d.fecha_vencimiento_licencia.strftime("%Y-%m-%d") if d.fecha_vencimiento_licencia else ""
            self.drivers_table.setItem(r, 3, QTableWidgetItem(v_str))
        self.drivers_table.setEnabled(False)

        self._recalculate_quote()

    def _save_contract(self) -> None:
        """Valida y persiste el contrato formalizado."""
        client_id = self.client_combo.currentData()
        veh_id = self.vehicle_combo.currentData()
        coverage_id = self.coverage_combo.currentData()

        if not client_id:
            QMessageBox.warning(self, "Campo Requerido", "Debe seleccionar un cliente para el contrato.")
            return

        if not veh_id:
            QMessageBox.warning(self, "Campo Requerido", "Debe seleccionar un vehículo a entregar.")
            return

        if not coverage_id:
            QMessageBox.warning(self, "Campo Requerido", "Debe seleccionar una cobertura de seguro.")
            return

        start_dt = self.start_date_edit.dateTime().toPython()
        end_dt = self.end_date_edit.dateTime().toPython()

        if end_dt <= start_dt:
            QMessageBox.warning(self, "Fechas Inválidas", "La fecha de fin debe ser posterior a la fecha de inicio.")
            return

        # Recoger conductores adicionales
        additional_drivers: List[AdditionalDriver] = []
        for r in range(self.drivers_table.rowCount()):
            name = (self.drivers_table.item(r, 0).text() if self.drivers_table.item(r, 0) else "").strip()
            ident = (self.drivers_table.item(r, 1).text() if self.drivers_table.item(r, 1) else "").strip()
            lic = (self.drivers_table.item(r, 2).text() if self.drivers_table.item(r, 2) else "").strip()
            exp_str = (self.drivers_table.item(r, 3).text() if self.drivers_table.item(r, 3) else "").strip()

            if name or ident or lic:
                if not (name and ident and lic and exp_str):
                    QMessageBox.warning(
                        self,
                        "Conductor Incompleto",
                        f"Complete todos los campos del conductor adicional #{r + 1} o elimine la fila.",
                    )
                    return
                try:
                    exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
                except ValueError:
                    QMessageBox.warning(
                        self,
                        "Formato de Fecha",
                        f"La fecha de vencimiento del conductor #{r + 1} debe tener formato YYYY-MM-DD.",
                    )
                    return

                additional_drivers.append(
                    AdditionalDriver(
                        nombre_completo=name,
                        identificacion=ident,
                        numero_licencia=lic,
                        fecha_vencimiento_licencia=exp_date,
                    )
                )

        new_contract = Contract(
            id_reserva=self.reservation.id_reserva if self.reservation else None,
            id_cliente=client_id,
            id_vehiculo=veh_id,
            id_cobertura=coverage_id,
            fecha_hora_inicio_pactada=start_dt,
            fecha_hora_fin_pactada=end_dt,
            fecha_hora_salida_real=datetime.now(),
            kilometraje_salida=self.km_salida_spin.value(),
            combustible_salida=Decimal(str(self.fuel_combo.currentData())),
            tarifa_diaria_aplicada=Decimal(str(self.tarifa_spin.value())),
            monto_garantia=Decimal(str(self.garantia_spin.value())),
            kilometraje_ilimitado=True,
            costo_km_excedente=Decimal("0.00"),
            conductores_adicionales=additional_drivers,
        )

        try:
            created = contract_service.create_contract(
                new_contract,
                metodo_pago_garantia=self.metodo_combo.currentData(),
                referencia_pago_garantia=self.referencia_input.text().strip(),
            )
            QMessageBox.information(
                self,
                "Contrato Emitido Exitosamente",
                f"Contrato formalizado con código: {created.codigo_contrato}\n\n"
                f"• Vehículo: {created.id_vehiculo} marcado como ALQUILADO\n"
                f"• Depósito de Garantía: ${created.monto_garantia}\n"
                f"• Entrega física registrada a las {created.fecha_hora_salida_real.strftime('%H:%M:%S')}",
            )
            self.accept()
        except AppException as e:
            QMessageBox.warning(self, "Regla de Negocio Incumplida", e.message)
        except Exception as e:
            logger.error("Error inesperado al emitir contrato: %s", e)
            QMessageBox.critical(self, "Error del Sistema", f"Ocurrió un error no controlado: {e}")
