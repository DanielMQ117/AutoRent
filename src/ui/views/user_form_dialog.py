"""Diálogo modal para el registro y modificación de cuentas de usuario (Fase 10)."""

from typing import List, Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.exceptions import AppException
from src.domain.models import Role, User
from src.services.user_service import user_service


class UserFormDialog(QDialog):
    """Formulario modal para crear o editar usuarios y asignar roles del sistema."""

    def __init__(self, user: Optional[User] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.user = user
        self.is_edit_mode = user is not None
        self.roles_list: List[Role] = []
        self._init_ui()
        self._load_roles()
        if self.is_edit_mode and self.user:
            self._populate_fields(self.user)

    def _init_ui(self) -> None:
        title_text = "Nuevo Usuario del Sistema" if not self.is_edit_mode else f"Editar Usuario — @{self.user.username}"
        self.setWindowTitle(title_text)
        self.resize(540, 560 if not self.is_edit_mode else 480)
        self.setMinimumSize(480, 480 if not self.is_edit_mode else 420)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
            }
            QLabel {
                color: #cbd5e1;
                font-size: 9pt;
            }
            QLineEdit, QComboBox {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 9pt;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #38bdf8;
            }
            QLineEdit:disabled, QComboBox:disabled {
                background-color: #0f172a;
                color: #64748b;
                border: 1px solid #1e293b;
            }
            QCheckBox {
                color: #e2e8f0;
                font-size: 9pt;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #475569;
                background-color: #1e293b;
            }
            QCheckBox::indicator:checked {
                background-color: #0284c7;
                border-color: #38bdf8;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        # Encabezado
        title = QLabel(f"👤 {title_text}")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8;")
        layout.addWidget(title)

        # Campo: Nombre Completo
        layout.addWidget(QLabel("Nombre Completo:"))
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Ej: Carlos Fonseca Amador")
        layout.addWidget(self.txt_nombre)

        # Fila: Username y Email
        row_creds = QHBoxLayout()
        row_creds.setSpacing(10)

        col_user = QVBoxLayout()
        col_user.setSpacing(4)
        col_user.addWidget(QLabel("Nombre de Usuario:"))
        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("Ej: cfonseca")
        if self.is_edit_mode:
            self.txt_username.setEnabled(False)
            self.txt_username.setToolTip("El identificador de usuario no puede ser alterado.")
        col_user.addWidget(self.txt_username)
        row_creds.addLayout(col_user)

        col_email = QVBoxLayout()
        col_email.setSpacing(4)
        col_email.addWidget(QLabel("Correo Electrónico:"))
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("Ej: usuario@rentacar.com")
        col_email.addWidget(self.txt_email)
        row_creds.addLayout(col_email)

        layout.addLayout(row_creds)

        # Campo: Rol
        layout.addWidget(QLabel("Rol en el Sistema (RBAC):"))
        self.cmb_rol = QComboBox()
        layout.addWidget(self.cmb_rol)

        # Campos de Contraseña (Solo en Modo Creación)
        if not self.is_edit_mode:
            row_pwd = QHBoxLayout()
            row_pwd.setSpacing(10)

            col_p1 = QVBoxLayout()
            col_p1.setSpacing(4)
            col_p1.addWidget(QLabel("Contraseña (mínimo 6 car.):"))
            self.txt_password = QLineEdit()
            self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
            self.txt_password.setPlaceholderText("••••••••")
            col_p1.addWidget(self.txt_password)
            row_pwd.addLayout(col_p1)

            col_p2 = QVBoxLayout()
            col_p2.setSpacing(4)
            col_p2.addWidget(QLabel("Confirmar Contraseña:"))
            self.txt_confirm_pwd = QLineEdit()
            self.txt_confirm_pwd.setEchoMode(QLineEdit.EchoMode.Password)
            self.txt_confirm_pwd.setPlaceholderText("••••••••")
            col_p2.addWidget(self.txt_confirm_pwd)
            row_pwd.addLayout(col_p2)

            layout.addLayout(row_pwd)

        # Estado Activo
        self.chk_activo = QCheckBox("Cuenta Activa y Habilitada para Inicio de Sesión")
        self.chk_activo.setChecked(True)
        layout.addWidget(self.chk_activo)

        # Si es el Administrador primario (ID 1 o 'admin'), proteger rol y estado
        if self.is_edit_mode and self.user and (self.user.id_usuario == 1 or self.user.username.lower() == "admin"):
            self.cmb_rol.setEnabled(False)
            self.cmb_rol.setToolTip("El rol del Administrador principal no puede ser modificado.")
            self.chk_activo.setEnabled(False)
            self.chk_activo.setChecked(True)
            self.chk_activo.setToolTip("La cuenta del Administrador principal debe permanecer siempre activa.")

        layout.addStretch()

        # Botones de Acción
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setFont(QFont("Segoe UI", 9))
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #e2e8f0;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 7px 16px;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Guardar Usuario" if not self.is_edit_mode else "Guardar Cambios")
        self.btn_save.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 7px 18px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        self.btn_save.clicked.connect(self._handle_save)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _load_roles(self) -> None:
        """Carga la lista de roles del sistema en el combobox."""
        try:
            self.roles_list = user_service.list_roles()
            self.cmb_rol.clear()
            for r in self.roles_list:
                self.cmb_rol.addItem(f"{r.nombre} — {r.descripcion}", userData=r.id_rol)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los roles: {e}")

    def _populate_fields(self, user: User) -> None:
        """Rellena los controles con la información del usuario a editar."""
        self.txt_nombre.setText(user.nombre_completo)
        self.txt_username.setText(user.username)
        self.txt_email.setText(user.email)
        self.chk_activo.setChecked(user.activo)

        # Seleccionar rol correspondiente
        for idx in range(self.cmb_rol.count()):
            if self.cmb_rol.itemData(idx) == user.id_rol:
                self.cmb_rol.setCurrentIndex(idx)
                break

    def _handle_save(self) -> None:
        """Valida y persiste los cambios."""
        nombre = self.txt_nombre.text().strip()
        username = self.txt_username.text().strip()
        email = self.txt_email.text().strip().lower()
        id_rol = self.cmb_rol.currentData()
        activo = self.chk_activo.isChecked()

        if not id_rol:
            QMessageBox.warning(self, "Rol Requerido", "Por favor seleccione un rol válido.")
            return

        try:
            if not self.is_edit_mode:
                password = self.txt_password.text()
                confirm = self.txt_confirm_pwd.text()

                if len(password) < 6:
                    QMessageBox.warning(self, "Contraseña Débil", "La contraseña debe tener al menos 6 caracteres.")
                    self.txt_password.setFocus()
                    return

                if password != confirm:
                    QMessageBox.warning(self, "No Coinciden", "Las contraseñas ingresadas no coinciden.")
                    self.txt_confirm_pwd.selectAll()
                    self.txt_confirm_pwd.setFocus()
                    return

                user_service.create_user(
                    username=username,
                    password=password,
                    nombre_completo=nombre,
                    email=email,
                    id_rol=id_rol,
                    activo=activo,
                )
                QMessageBox.information(
                    self,
                    "Usuario Registrado",
                    f"La cuenta de usuario @{username} ha sido creada satisfactoriamente.",
                )
            else:
                if not self.user or not self.user.id_usuario:
                    return
                user_service.update_user(
                    id_usuario=self.user.id_usuario,
                    nombre_completo=nombre,
                    email=email,
                    id_rol=id_rol,
                    activo=activo,
                )
                QMessageBox.information(
                    self,
                    "Usuario Actualizado",
                    f"Los datos del usuario @{self.user.username} han sido actualizados con éxito.",
                )

            self.accept()
        except AppException as e:
            QMessageBox.critical(self, "Validación Fallida", e.message)
        except Exception as e:
            QMessageBox.critical(self, "Error Inesperado", f"Ocurrió un error al guardar: {e}")
