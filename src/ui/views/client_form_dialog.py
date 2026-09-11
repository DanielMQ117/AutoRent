"""Diálogo modal para el registro y edición integral de Clientes y Licencias."""

from datetime import date
from typing import Optional
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.exceptions import AppException
from src.core.logger import get_logger
from src.domain.enums import ClientStatus, ClientType
from src.domain.models import Client, DriverLicense
from src.services.client_service import client_service

logger = get_logger(__name__)


class ClientFormDialog(QDialog):
    """Formulario modal para crear o editar expedientes de clientes."""

    def __init__(self, parent: Optional[QWidget] = None, client: Optional[Client] = None) -> None:
        super().__init__(parent)
        self.client = client
        self.is_edit_mode = client is not None
        self._init_ui()
        if self.is_edit_mode:
            self._load_client_data()

    def _init_ui(self) -> None:
        """Inicializa la interfaz gráfica del diálogo modal."""
        title = "Editar Cliente" if self.is_edit_mode else "Registrar Nuevo Cliente"
        self.setWindowTitle(f"AutoRent Pro — {title}")
        self.resize(650, 680)
        self.setMinimumSize(580, 600)
        self.setStyleSheet("background-color: #0f172a; color: #f8fafc;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(15)

        # 1. Cabecera
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        header_title = QLabel(title)
        header_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_title.setStyleSheet("color: #38bdf8;")

        header_desc = QLabel(
            "Complete los datos del arrendatario. Los campos marcados con (*) son obligatorios."
        )
        header_desc.setFont(QFont("Segoe UI", 9))
        header_desc.setStyleSheet("color: #94a3b8;")

        header_layout.addWidget(header_title)
        header_layout.addWidget(header_desc)
        main_layout.addLayout(header_layout)

        # 2. Banner de Error
        self.error_label = QLabel("")
        self.error_label.setFont(QFont("Segoe UI", 9))
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("""
            background-color: rgba(239, 68, 68, 0.15);
            color: #fca5a5;
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 6px;
            padding: 8px 12px;
        """)
        self.error_label.hide()
        main_layout.addWidget(self.error_label)

        # 3. Área de Scroll con los formularios
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(16)
        container_layout.setContentsMargins(0, 0, 0, 0)

        # Card 1: Datos Personales y Fiscales
        card_personal = self._create_card("1. Información Personal y de Contacto")
        grid_personal = QGridLayout()
        grid_personal.setSpacing(12)

        # Tipo de Persona
        grid_personal.addWidget(self._create_field_label("Tipo de Persona *"), 0, 0)
        self.tipo_persona_combo = QComboBox()
        self.tipo_persona_combo.addItem("Persona Natural", ClientType.NATURAL.value)
        self.tipo_persona_combo.addItem("Persona Jurídica", ClientType.JURIDICA.value)
        self._style_input(self.tipo_persona_combo)
        grid_personal.addWidget(self.tipo_persona_combo, 0, 1)

        # Identificación
        grid_personal.addWidget(self._create_field_label("Identificación / Cédula / RUC *"), 1, 0)
        self.identificacion_input = QLineEdit()
        self.identificacion_input.setPlaceholderText("Ej: 001-150898-0023K o J0310000123456")
        self._style_input(self.identificacion_input)
        grid_personal.addWidget(self.identificacion_input, 1, 1)

        # Nombres
        grid_personal.addWidget(self._create_field_label("Nombres / Razón Social *"), 2, 0)
        self.nombres_input = QLineEdit()
        self.nombres_input.setPlaceholderText("Nombres del cliente")
        self._style_input(self.nombres_input)
        grid_personal.addWidget(self.nombres_input, 2, 1)

        # Apellidos
        grid_personal.addWidget(self._create_field_label("Apellidos / Representante *"), 3, 0)
        self.apellidos_input = QLineEdit()
        self.apellidos_input.setPlaceholderText("Apellidos o Representante Legal")
        self._style_input(self.apellidos_input)
        grid_personal.addWidget(self.apellidos_input, 3, 1)

        # Teléfono
        grid_personal.addWidget(self._create_field_label("Teléfono *"), 4, 0)
        self.telefono_input = QLineEdit()
        self.telefono_input.setPlaceholderText("+505-8899-1122")
        self._style_input(self.telefono_input)
        grid_personal.addWidget(self.telefono_input, 4, 1)

        # Correo Electrónico
        grid_personal.addWidget(self._create_field_label("Correo Electrónico *"), 5, 0)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("correo@dominio.com")
        self._style_input(self.email_input)
        grid_personal.addWidget(self.email_input, 5, 1)

        # Dirección
        grid_personal.addWidget(self._create_field_label("Dirección Domiciliar *"), 6, 0)
        self.direccion_input = QTextEdit()
        self.direccion_input.setPlaceholderText("Dirección completa de residencia o empresa")
        self.direccion_input.setMaximumHeight(70)
        self._style_input(self.direccion_input)
        grid_personal.addWidget(self.direccion_input, 6, 1)

        # Estado del Cliente
        grid_personal.addWidget(self._create_field_label("Estado Comercial *"), 7, 0)
        self.estado_combo = QComboBox()
        self.estado_combo.addItem("ACTIVO (Habilitado para contratos)", ClientStatus.ACTIVO.value)
        self.estado_combo.addItem("MOROSO (Pendiente de pago)", ClientStatus.MOROSO.value)
        self.estado_combo.addItem("VETADO (Prohibido el servicio)", ClientStatus.VETADO.value)
        self._style_input(self.estado_combo)
        grid_personal.addWidget(self.estado_combo, 7, 1)

        card_personal.layout().addLayout(grid_personal)
        container_layout.addWidget(card_personal)

        # Card 2: Licencia de Conducir
        card_licencia = self._create_card("2. Licencia de Conducir del Arrendatario")
        licencia_layout = QVBoxLayout()
        licencia_layout.setSpacing(12)

        self.has_licencia_check = QCheckBox("Registrar datos de licencia de conducir")
        self.has_licencia_check.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        self.has_licencia_check.setStyleSheet("color: #38bdf8;")
        self.has_licencia_check.toggled.connect(self._toggle_license_fields)
        licencia_layout.addWidget(self.has_licencia_check)

        self.license_container = QWidget()
        grid_lic = QGridLayout(self.license_container)
        grid_lic.setContentsMargins(0, 0, 0, 0)
        grid_lic.setSpacing(12)

        # Número de Licencia
        grid_lic.addWidget(self._create_field_label("Número de Licencia *"), 0, 0)
        self.num_licencia_input = QLineEdit()
        self.num_licencia_input.setPlaceholderText("Ej: LIC-001150898")
        self._style_input(self.num_licencia_input)
        grid_lic.addWidget(self.num_licencia_input, 0, 1)

        # Categoría de Licencia
        grid_lic.addWidget(self._create_field_label("Categoría *"), 1, 0)
        self.categoria_lic_combo = QComboBox()
        self.categoria_lic_combo.addItems(["CATEGORIA_1", "CATEGORIA_2", "CATEGORIA_3", "CATEGORIA_4", "CATEGORIA_5"])
        self.categoria_lic_combo.setCurrentText("CATEGORIA_3")
        self._style_input(self.categoria_lic_combo)
        grid_lic.addWidget(self.categoria_lic_combo, 1, 1)

        # País de Emisión
        grid_lic.addWidget(self._create_field_label("País de Emisión *"), 2, 0)
        self.pais_lic_input = QLineEdit("Nicaragua")
        self._style_input(self.pais_lic_input)
        grid_lic.addWidget(self.pais_lic_input, 2, 1)

        # Fecha de Emisión
        grid_lic.addWidget(self._create_field_label("Fecha de Emisión *"), 3, 0)
        self.fecha_emision_edit = QDateEdit()
        self.fecha_emision_edit.setCalendarPopup(True)
        self.fecha_emision_edit.setDate(QDate.currentDate().addYears(-2))
        self._style_input(self.fecha_emision_edit)
        grid_lic.addWidget(self.fecha_emision_edit, 3, 1)

        # Fecha de Vencimiento
        grid_lic.addWidget(self._create_field_label("Fecha de Vencimiento *"), 4, 0)
        self.fecha_vencimiento_edit = QDateEdit()
        self.fecha_vencimiento_edit.setCalendarPopup(True)
        self.fecha_vencimiento_edit.setDate(QDate.currentDate().addYears(3))
        self._style_input(self.fecha_vencimiento_edit)
        grid_lic.addWidget(self.fecha_vencimiento_edit, 4, 1)

        licencia_layout.addWidget(self.license_container)
        card_licencia.layout().addLayout(licencia_layout)
        container_layout.addWidget(card_licencia)

        # Por defecto deshabilitar campos de licencia hasta que se marque el checkbox
        self.license_container.setEnabled(False)

        scroll.setWidget(container)
        main_layout.addWidget(scroll, stretch=1)

        # 4. Botonera de Acción Inferior
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(12)

        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #e2e8f0;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)

        self.save_btn = QPushButton("Guardar Cambios" if self.is_edit_mode else "Registrar Cliente")
        self.save_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
            QPushButton:disabled {
                background-color: #1e293b;
                color: #64748b;
            }
        """)
        self.save_btn.clicked.connect(self._handle_save)

        btn_bar.addStretch()
        btn_bar.addWidget(self.cancel_btn)
        btn_bar.addWidget(self.save_btn)
        main_layout.addLayout(btn_bar)

    def _create_card(self, title: str) -> QFrame:
        """Crea una tarjeta contenedora de formulario con título."""
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
        layout.setSpacing(12)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #f1f5f9; border: none;")
        layout.addWidget(title_lbl)

        return card

    @staticmethod
    def _create_field_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        lbl.setStyleSheet("color: #cbd5e1; border: none;")
        return lbl

    @staticmethod
    def _style_input(widget: QWidget) -> None:
        widget.setStyleSheet("""
            QLineEdit, QTextEdit, QComboBox, QDateEdit {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 10px;
                font-family: 'Segoe UI';
                font-size: 10pt;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus {
                border: 1px solid #38bdf8;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                color: #f8fafc;
                selection-background-color: #0284c7;
                border: 1px solid #334155;
            }
        """)

    def _toggle_license_fields(self, checked: bool) -> None:
        """Habilita o deshabilita los controles de licencia según el checkbox."""
        self.license_container.setEnabled(checked)

    def _load_client_data(self) -> None:
        """Carga en el formulario los datos del cliente a editar."""
        if not self.client:
            return

        # Tipo persona
        idx = self.tipo_persona_combo.findData(self.client.tipo_persona.value)
        if idx >= 0:
            self.tipo_persona_combo.setCurrentIndex(idx)

        self.identificacion_input.setText(self.client.identificacion)
        self.nombres_input.setText(self.client.nombres)
        self.apellidos_input.setText(self.client.apellidos)
        self.telefono_input.setText(self.client.telefono)
        self.email_input.setText(self.client.email)
        self.direccion_input.setPlainText(self.client.direccion)

        # Estado
        idx_st = self.estado_combo.findData(self.client.estado_cliente.value)
        if idx_st >= 0:
            self.estado_combo.setCurrentIndex(idx_st)

        # Licencia
        if self.client.licencia:
            self.has_licencia_check.setChecked(True)
            self.num_licencia_input.setText(self.client.licencia.numero_licencia)
            idx_cat = self.categoria_lic_combo.findText(self.client.licencia.categoria_licencia)
            if idx_cat >= 0:
                self.categoria_lic_combo.setCurrentIndex(idx_cat)
            self.pais_lic_input.setText(self.client.licencia.pais_emision or "Nicaragua")

            if self.client.licencia.fecha_emision:
                d = self.client.licencia.fecha_emision
                self.fecha_emision_edit.setDate(QDate(d.year, d.month, d.day))

            if self.client.licencia.fecha_vencimiento:
                d = self.client.licencia.fecha_vencimiento
                self.fecha_vencimiento_edit.setDate(QDate(d.year, d.month, d.day))

    def _handle_save(self) -> None:
        """Valida y guarda el cliente a través del servicio BLL."""
        self.error_label.hide()

        tipo_persona = ClientType(self.tipo_persona_combo.currentData())
        identificacion = self.identificacion_input.text().strip()
        nombres = self.nombres_input.text().strip()
        apellidos = self.apellidos_input.text().strip()
        telefono = self.telefono_input.text().strip()
        email = self.email_input.text().strip()
        direccion = self.direccion_input.toPlainText().strip()
        estado = ClientStatus(self.estado_combo.currentData())

        license_obj: Optional[DriverLicense] = None
        if self.has_licencia_check.isChecked():
            num_lic = self.num_licencia_input.text().strip()
            cat_lic = self.categoria_lic_combo.currentText().strip()
            pais_lic = self.pais_lic_input.text().strip() or "Nicaragua"
            q_emision = self.fecha_emision_edit.date()
            q_vencimiento = self.fecha_vencimiento_edit.date()

            d_emision = date(q_emision.year(), q_emision.month(), q_emision.day())
            d_vencimiento = date(q_vencimiento.year(), q_vencimiento.month(), q_vencimiento.day())

            license_obj = DriverLicense(
                numero_licencia=num_lic,
                categoria_licencia=cat_lic,
                pais_emision=pais_lic,
                fecha_emision=d_emision,
                fecha_vencimiento=d_vencimiento,
            )

        try:
            if self.is_edit_mode and self.client:
                # Actualización
                self.client.tipo_persona = tipo_persona
                self.client.identificacion = identificacion
                self.client.nombres = nombres
                self.client.apellidos = apellidos
                self.client.telefono = telefono
                self.client.email = email
                self.client.direccion = direccion
                self.client.estado_cliente = estado

                client_service.update_client(self.client, license_obj)
                QMessageBox.information(self, "Éxito", f"Expediente del cliente '{self.client.nombre_completo}' actualizado exitosamente.")
            else:
                # Creación
                new_c = Client(
                    tipo_persona=tipo_persona,
                    identificacion=identificacion,
                    nombres=nombres,
                    apellidos=apellidos,
                    telefono=telefono,
                    email=email,
                    direccion=direccion,
                    estado_cliente=estado,
                )
                created = client_service.create_client(new_c, license_obj)
                QMessageBox.information(self, "Éxito", f"Cliente '{created.nombre_completo}' registrado con éxito en el sistema.")

            self.accept()

        except AppException as e:
            self.error_label.setText(f"⚠ {e.message}")
            self.error_label.show()
        except Exception as e:
            logger.error("Error inesperado en formulario de cliente: %s", e)
            self.error_label.setText(f"Error inesperado del servidor: {e}")
            self.error_label.show()
