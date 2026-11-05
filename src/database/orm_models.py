"""Modelos Declarativos SQLAlchemy 2.0 ORM para las 19 tablas del esquema PostgreSQL."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.orm_base import Base
from src.domain.enums import (
    ClientStatus,
    ClientType,
    ContractStatus,
    DamageSeverity,
    DamageType,
    MaintenanceStatus,
    MaintenanceType,
    PaymentMethod,
    PaymentType,
    ReservationStatus,
    SettlementStatus,
    VehicleStatus,
)
from src.domain.models import (
    AdditionalDriver,
    Agency,
    AuditLog,
    Brand,
    Client,
    Contract,
    Damage,
    DriverLicense,
    InsuranceCoverage,
    Maintenance,
    Payment,
    Reservation,
    ReturnInspection,
    Role,
    Settlement,
    User,
    Vehicle,
    VehicleCategory,
    VehicleModel,
)


# ============================================================================
# 0. MÓDULO MULTI-TENANCY (AGENCIAS / INQUILINOS)
# ============================================================================


class AgenciaORM(Base):
    """Modelo ORM para la tabla global ``agencias`` (Sedes / Inquilinos Multi-Tenant)."""

    __tablename__ = "agencias"

    id_agencia: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo_agencia: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nombre_comercial: Mapped[str] = mapped_column(String(100), nullable=False)
    ruc_nit: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    telefono: Mapped[str] = mapped_column(String(25), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    direccion: Mapped[str] = mapped_column(Text, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def to_domain(self) -> Agency:
        """Convierte la instancia ORM ``AgenciaORM`` al modelo de dominio ``Agency``.

        Returns:
            Agency: Objeto de dominio puro con los datos de la sucursal.
        """
        return Agency(
            id_agencia=self.id_agencia,
            codigo_agencia=self.codigo_agencia,
            nombre_comercial=self.nombre_comercial,
            ruc_nit=self.ruc_nit,
            telefono=self.telefono,
            email=self.email,
            direccion=self.direccion,
            activo=self.activo,
            fecha_creacion=self.fecha_creacion,
        )


# ============================================================================
# 1. MÓDULO DE SEGURIDAD Y USUARIOS
# ============================================================================


class RolORM(Base):
    """Modelo ORM para la tabla catálogo ``roles`` (RBAC)."""

    __tablename__ = "roles"
    __table_args__ = (
        CheckConstraint(
            "nombre IN ('ADMINISTRADOR', 'AGENTE_VENTAS', 'INSPECTOR_TALLER', 'GERENTE')",
            name="chk_rol_nombre",
        ),
    )

    id_rol: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    descripcion: Mapped[str] = mapped_column(String(200), nullable=False)

    def to_domain(self) -> Role:
        """Convierte la instancia ORM ``RolORM`` al modelo de dominio ``Role``.

        Returns:
            Role: Objeto de dominio con los datos del rol de seguridad.
        """
        return Role(
            id_rol=self.id_rol,
            nombre=self.nombre,
            descripcion=self.descripcion,
        )


class UsuarioORM(Base):
    """Modelo ORM para la tabla multi-tenant ``usuarios``."""

    __tablename__ = "usuarios"
    __table_args__ = (
        UniqueConstraint("tenant_id", "username", name="uq_usuarios_tenant_username"),
        UniqueConstraint("tenant_id", "email", name="uq_usuarios_tenant_email"),
    )

    id_usuario: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agencias.id_agencia", ondelete="RESTRICT"), nullable=False
    )
    id_rol: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("roles.id_rol", ondelete="RESTRICT"), nullable=False
    )
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre_completo: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    rol: Mapped[Optional["RolORM"]] = relationship("RolORM", lazy="joined")
    agencia: Mapped[Optional["AgenciaORM"]] = relationship("AgenciaORM", lazy="joined")

    def to_domain(self) -> User:
        """Convierte la instancia ORM ``UsuarioORM`` al modelo de dominio ``User``.

        Returns:
            User: Entidad de dominio con nombre de rol y agencia resueltos.
        """
        return User(
            id_usuario=self.id_usuario,
            tenant_id=self.tenant_id,
            id_rol=self.id_rol,
            username=self.username,
            password_hash=self.password_hash,
            nombre_completo=self.nombre_completo,
            email=self.email,
            activo=self.activo,
            fecha_creacion=self.fecha_creacion,
            rol_nombre=self.rol.nombre if self.rol else None,
            agencia_nombre=self.agencia.nombre_comercial if self.agencia else None,
            agencia_codigo=self.agencia.codigo_agencia if self.agencia else None,
        )


class AuditoriaORM(Base):
    """Modelo ORM para la bitácora inmutable multi-tenant ``auditoria``."""

    __tablename__ = "auditoria"

    id_auditoria: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agencias.id_agencia", ondelete="RESTRICT"), nullable=False
    )
    id_usuario: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True
    )
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    accion: Mapped[str] = mapped_column(String(60), nullable=False)
    tabla_afectada: Mapped[str] = mapped_column(String(60), nullable=False)
    id_registro: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    detalles: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_origen: Mapped[str] = mapped_column(String(45), default="127.0.0.1", nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def to_domain(self) -> AuditLog:
        """Convierte la instancia ORM ``AuditoriaORM`` al modelo de dominio ``AuditLog``.

        Returns:
            AuditLog: Registro de auditoría de dominio.
        """
        return AuditLog(
            id_auditoria=self.id_auditoria,
            tenant_id=self.tenant_id,
            id_usuario=self.id_usuario,
            username=self.username,
            accion=self.accion,
            tabla_afectada=self.tabla_afectada,
            id_registro=self.id_registro,
            detalles=self.detalles,
            ip_origen=self.ip_origen,
            fecha_registro=self.fecha_registro,
        )


# ============================================================================
# 2. MÓDULO DE FLOTA Y VEHÍCULOS
# ============================================================================


class MarcaORM(Base):
    """Modelo ORM para la tabla catálogo global ``marcas``."""

    __tablename__ = "marcas"

    id_marca: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    def to_domain(self) -> Brand:
        """Convierte la instancia ORM ``MarcaORM`` al modelo de dominio ``Brand``.

        Returns:
            Brand: Marca automotriz de dominio.
        """
        return Brand(id_marca=self.id_marca, nombre=self.nombre)


class ModeloORM(Base):
    """Modelo ORM para la tabla catálogo global ``modelos``."""

    __tablename__ = "modelos"
    __table_args__ = (
        UniqueConstraint("id_marca", "nombre", "anio", name="uq_modelo_marca_anio"),
        CheckConstraint(
            "tipo_transmision IN ('MANUAL', 'AUTOMATICA')",
            name="chk_modelo_transmision",
        ),
        CheckConstraint("capacidad_pasajeros > 0", name="chk_modelo_pasajeros"),
    )

    id_modelo: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    id_marca: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("marcas.id_marca", ondelete="RESTRICT"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo_transmision: Mapped[str] = mapped_column(String(20), nullable=False)
    capacidad_pasajeros: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    marca: Mapped[Optional["MarcaORM"]] = relationship("MarcaORM", lazy="joined")

    def to_domain(self) -> VehicleModel:
        """Convierte la instancia ORM ``ModeloORM`` al modelo de dominio ``VehicleModel``.

        Returns:
            VehicleModel: Modelo automotriz con el nombre de su marca.
        """
        return VehicleModel(
            id_modelo=self.id_modelo,
            id_marca=self.id_marca,
            nombre=self.nombre,
            anio=self.anio,
            tipo_transmision=self.tipo_transmision,
            capacidad_pasajeros=self.capacidad_pasajeros,
            marca_nombre=self.marca.nombre if self.marca else None,
        )


class CategoriaVehiculoORM(Base):
    """Modelo ORM para la tabla multi-tenant ``categorias_vehiculo``."""

    __tablename__ = "categorias_vehiculo"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nombre", name="uq_categorias_tenant_nombre"),
        CheckConstraint("deposito_garantia_sugerido >= 0", name="chk_categoria_garantia"),
        CheckConstraint("tarifa_base_diaria > 0", name="chk_categoria_tarifa"),
    )

    id_categoria: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agencias.id_agencia", ondelete="RESTRICT"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deposito_garantia_sugerido: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("300.00"), nullable=False
    )
    tarifa_base_diaria: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    def to_domain(self) -> VehicleCategory:
        """Convierte la instancia ORM ``CategoriaVehiculoORM`` al modelo ``VehicleCategory``.

        Returns:
            VehicleCategory: Categoría tarifaria de dominio.
        """
        return VehicleCategory(
            id_categoria=self.id_categoria,
            tenant_id=self.tenant_id,
            nombre=self.nombre,
            descripcion=self.descripcion,
            deposito_garantia_sugerido=Decimal(str(self.deposito_garantia_sugerido)),
            tarifa_base_diaria=Decimal(str(self.tarifa_base_diaria)),
        )


class VehiculoORM(Base):
    """Modelo ORM para la tabla multi-tenant ``vehiculos``."""

    __tablename__ = "vehiculos"
    __table_args__ = (
        UniqueConstraint("tenant_id", "placa", name="uq_vehiculos_tenant_placa"),
        UniqueConstraint("tenant_id", "vin", name="uq_vehiculos_tenant_vin"),
        CheckConstraint("kilometraje_actual >= 0", name="chk_vehiculo_km"),
        CheckConstraint(
            "nivel_combustible_actual >= 0.00 AND nivel_combustible_actual <= 1.00",
            name="chk_vehiculo_combustible",
        ),
        CheckConstraint(
            "km_proximo_mantenimiento > 0",
            name="chk_vehiculo_km_mantenimiento",
        ),
        CheckConstraint(
            "estado IN ('DISPONIBLE', 'RESERVADO', 'ALQUILADO', 'EN_INSPECCION', 'EN_MANTENIMIENTO', 'DE_BAJA')",
            name="chk_vehiculo_estado",
        ),
    )

    id_vehiculo: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agencias.id_agencia", ondelete="RESTRICT"), nullable=False
    )
    id_modelo: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("modelos.id_modelo", ondelete="RESTRICT"), nullable=False
    )
    id_categoria: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("categorias_vehiculo.id_categoria", ondelete="RESTRICT"),
        nullable=False,
    )
    placa: Mapped[str] = mapped_column(String(20), nullable=False)
    vin: Mapped[str] = mapped_column(String(17), nullable=False)
    color: Mapped[str] = mapped_column(String(30), nullable=False)
    kilometraje_actual: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    nivel_combustible_actual: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), default=Decimal("1.00"), nullable=False
    )
    estado: Mapped[str] = mapped_column(String(25), default="DISPONIBLE", nullable=False)
    km_proximo_mantenimiento: Mapped[int] = mapped_column(Integer, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    modelo: Mapped[Optional["ModeloORM"]] = relationship("ModeloORM", lazy="joined")
    categoria: Mapped[Optional["CategoriaVehiculoORM"]] = relationship(
        "CategoriaVehiculoORM", lazy="joined"
    )

    def to_domain(self) -> Vehicle:
        """Convierte la instancia ORM ``VehiculoORM`` al modelo de dominio ``Vehicle``.

        Returns:
            Vehicle: Entidad de dominio con datos enriquecidos de modelo, marca y categoría.
        """
        marca_nombre = (
            self.modelo.marca.nombre if (self.modelo and self.modelo.marca) else None
        )
        return Vehicle(
            id_vehiculo=self.id_vehiculo,
            tenant_id=self.tenant_id,
            id_modelo=self.id_modelo,
            id_categoria=self.id_categoria,
            placa=self.placa,
            vin=self.vin,
            color=self.color,
            kilometraje_actual=self.kilometraje_actual,
            nivel_combustible_actual=Decimal(str(self.nivel_combustible_actual)),
            estado=VehicleStatus(self.estado),
            km_proximo_mantenimiento=self.km_proximo_mantenimiento,
            activo=self.activo,
            modelo_nombre=self.modelo.nombre if self.modelo else None,
            categoria_nombre=self.categoria.nombre if self.categoria else None,
            marca_nombre=marca_nombre,
            anio=self.modelo.anio if self.modelo else None,
            tarifa_base_diaria=(
                Decimal(str(self.categoria.tarifa_base_diaria))
                if self.categoria and self.categoria.tarifa_base_diaria is not None
                else None
            ),
        )


# ============================================================================
# 3. MÓDULO DE CLIENTES Y CONDUCTORES
# ============================================================================


class ClienteORM(Base):
    """Modelo ORM para la tabla multi-tenant ``clientes``."""

    __tablename__ = "clientes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "identificacion", name="uq_clientes_tenant_identificacion"),
        UniqueConstraint("tenant_id", "email", name="uq_clientes_tenant_email"),
        CheckConstraint("tipo_persona IN ('NATURAL', 'JURIDICA')", name="chk_cliente_tipo"),
        CheckConstraint(
            "estado_cliente IN ('ACTIVO', 'MOROSO', 'VETADO')",
            name="chk_cliente_estado",
        ),
    )

    id_cliente: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agencias.id_agencia", ondelete="RESTRICT"), nullable=False
    )
    tipo_persona: Mapped[str] = mapped_column(String(15), default="NATURAL", nullable=False)
    identificacion: Mapped[str] = mapped_column(String(30), nullable=False)
    nombres: Mapped[str] = mapped_column(String(80), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(80), nullable=False)
    telefono: Mapped[str] = mapped_column(String(25), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    direccion: Mapped[str] = mapped_column(Text, nullable=False)
    estado_cliente: Mapped[str] = mapped_column(String(20), default="ACTIVO", nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    licencia: Mapped[Optional["LicenciaConducirORM"]] = relationship(
        "LicenciaConducirORM",
        back_populates="cliente",
        uselist=False,
        lazy="joined",
        cascade="all, delete-orphan",
    )

    def to_domain(self) -> Client:
        """Convierte la instancia ORM ``ClienteORM`` y su licencia al modelo ``Client``.

        Returns:
            Client: Entidad de dominio Cliente con su ``DriverLicense`` anidada si existe.
        """
        return Client(
            id_cliente=self.id_cliente,
            tenant_id=self.tenant_id,
            tipo_persona=ClientType(self.tipo_persona),
            identificacion=self.identificacion,
            nombres=self.nombres,
            apellidos=self.apellidos,
            telefono=self.telefono,
            email=self.email,
            direccion=self.direccion,
            estado_cliente=ClientStatus(self.estado_cliente),
            fecha_registro=self.fecha_registro,
            licencia=self.licencia.to_domain() if self.licencia else None,
        )


class LicenciaConducirORM(Base):
    """Modelo ORM para la tabla multi-tenant ``licencias_conducir``."""

    __tablename__ = "licencias_conducir"
    __table_args__ = (
        UniqueConstraint("tenant_id", "numero_licencia", name="uq_licencias_tenant_numero"),
        CheckConstraint("fecha_vencimiento > fecha_emision", name="chk_licencia_fechas"),
    )

    id_licencia: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agencias.id_agencia", ondelete="RESTRICT"), nullable=False
    )
    id_cliente: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("clientes.id_cliente", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    numero_licencia: Mapped[str] = mapped_column(String(40), nullable=False)
    categoria_licencia: Mapped[str] = mapped_column(String(30), nullable=False)
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)
    pais_emision: Mapped[str] = mapped_column(String(50), default="Nicaragua", nullable=False)

    cliente: Mapped[Optional["ClienteORM"]] = relationship(
        "ClienteORM", back_populates="licencia"
    )

    def to_domain(self) -> DriverLicense:
        """Convierte la instancia ORM ``LicenciaConducirORM`` al modelo ``DriverLicense``.

        Returns:
            DriverLicense: Licencia de conducir de dominio.
        """
        return DriverLicense(
            id_licencia=self.id_licencia,
            tenant_id=self.tenant_id,
            id_cliente=self.id_cliente,
            numero_licencia=self.numero_licencia,
            categoria_licencia=self.categoria_licencia,
            fecha_emision=self.fecha_emision,
            fecha_vencimiento=self.fecha_vencimiento,
            pais_emision=self.pais_emision,
        )


class CoberturaSeguroORM(Base):
    """Modelo ORM para la tabla multi-tenant ``coberturas_seguro``."""

    __tablename__ = "coberturas_seguro"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nombre", name="uq_coberturas_tenant_nombre"),
        CheckConstraint("costo_diario >= 0.00", name="chk_seguro_costo"),
        CheckConstraint(
            "porcentaje_deducible >= 0.00 AND porcentaje_deducible <= 100.00",
            name="chk_seguro_deducible",
        ),
    )

    id_cobertura: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agencias.id_agencia", ondelete="RESTRICT"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    costo_diario: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    porcentaje_deducible: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("10.00"), nullable=False
    )

    def to_domain(self) -> InsuranceCoverage:
        """Convierte la instancia ORM ``CoberturaSeguroORM`` al modelo ``InsuranceCoverage``.

        Returns:
            InsuranceCoverage: Póliza/cobertura de seguro de dominio.
        """
        return InsuranceCoverage(
            id_cobertura=self.id_cobertura,
            tenant_id=self.tenant_id,
            nombre=self.nombre,
            descripcion=self.descripcion,
            costo_diario=Decimal(str(self.costo_diario)),
            porcentaje_deducible=Decimal(str(self.porcentaje_deducible)),
        )


# ============================================================================
# 4. MÓDULO DE RESERVAS
# ============================================================================


class ReservaORM(Base):
    """Modelo ORM para la tabla multi-tenant ``reservas``."""

    __tablename__ = "reservas"
    __table_args__ = (
        UniqueConstraint("tenant_id", "codigo_reserva", name="uq_reservas_tenant_codigo"),
        CheckConstraint("fecha_hora_fin > fecha_hora_inicio", name="chk_reserva_fechas"),
        CheckConstraint("monto_anticipo >= 0.00", name="chk_reserva_anticipo"),
        CheckConstraint(
            "estado IN ('PENDIENTE', 'CONFIRMADA', 'CANCELADA', 'VENCIDA', 'CONVERTIDA_A_CONTRATO')",
            name="chk_reserva_estado",
        ),
    )

    id_reserva: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agencias.id_agencia", ondelete="RESTRICT"), nullable=False
    )
    codigo_reserva: Mapped[str] = mapped_column(String(20), nullable=False)
    id_cliente: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("clientes.id_cliente", ondelete="RESTRICT"), nullable=False
    )
    id_categoria: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("categorias_vehiculo.id_categoria", ondelete="RESTRICT"),
        nullable=False,
    )
    id_vehiculo: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("vehiculos.id_vehiculo", ondelete="RESTRICT"), nullable=True
    )
    fecha_hora_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_hora_fin: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    monto_anticipo: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    estado: Mapped[str] = mapped_column(String(25), default="PENDIENTE", nullable=False)
    id_usuario: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuarios.id_usuario", ondelete="RESTRICT"), nullable=False
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    cliente: Mapped[Optional["ClienteORM"]] = relationship("ClienteORM", lazy="joined")
    categoria: Mapped[Optional["CategoriaVehiculoORM"]] = relationship(
        "CategoriaVehiculoORM", lazy="joined"
    )
    vehiculo: Mapped[Optional["VehiculoORM"]] = relationship("VehiculoORM", lazy="joined")
    usuario: Mapped[Optional["UsuarioORM"]] = relationship("UsuarioORM", lazy="joined")

    def to_domain(self) -> Reservation:
        """Convierte la instancia ORM ``ReservaORM`` al modelo de dominio ``Reservation``.

        Returns:
            Reservation: Reserva con datos relacionales de cliente, categoría, vehículo y usuario.
        """
        veh_modelo = None
        if self.vehiculo and self.vehiculo.modelo:
            marca_txt = (
                self.vehiculo.modelo.marca.nombre
                if self.vehiculo.modelo.marca
                else ""
            )
            veh_modelo = f"{marca_txt} {self.vehiculo.modelo.nombre}".strip()

        return Reservation(
            id_reserva=self.id_reserva,
            tenant_id=self.tenant_id,
            codigo_reserva=self.codigo_reserva,
            id_cliente=self.id_cliente,
            id_categoria=self.id_categoria,
            id_vehiculo=self.id_vehiculo,
            fecha_hora_inicio=self.fecha_hora_inicio,
            fecha_hora_fin=self.fecha_hora_fin,
            monto_anticipo=Decimal(str(self.monto_anticipo)),
            estado=ReservationStatus(self.estado),
            id_usuario=self.id_usuario,
            fecha_creacion=self.fecha_creacion,
            cliente_nombre=(
                f"{self.cliente.nombres} {self.cliente.apellidos}".strip()
                if self.cliente
                else None
            ),
            cliente_identificacion=self.cliente.identificacion if self.cliente else None,
            categoria_nombre=self.categoria.nombre if self.categoria else None,
            tarifa_base_diaria=(
                Decimal(str(self.categoria.tarifa_base_diaria))
                if self.categoria and self.categoria.tarifa_base_diaria is not None
                else None
            ),
            vehiculo_placa=self.vehiculo.placa if self.vehiculo else None,
            vehiculo_modelo=veh_modelo,
            usuario_nombre=self.usuario.nombre_completo if self.usuario else None,
        )


# ============================================================================
# 5. MÓDULO DE CONTRATOS Y OPERACIONES
# ============================================================================


class ContratoORM(Base):
    """Modelo ORM para la tabla multi-tenant ``contratos``."""

    __tablename__ = "contratos"
    __table_args__ = (
        UniqueConstraint("tenant_id", "codigo_contrato", name="uq_contratos_tenant_codigo"),
        CheckConstraint(
            "fecha_hora_fin_pactada > fecha_hora_inicio_pactada",
            name="chk_contrato_fechas",
        ),
        CheckConstraint("kilometraje_salida >= 0", name="chk_contrato_km_salida"),
        CheckConstraint(
            "combustible_salida >= 0.00 AND combustible_salida <= 1.00",
            name="chk_contrato_combustible",
        ),
        CheckConstraint("tarifa_diaria_aplicada > 0.00", name="chk_contrato_tarifa"),
        CheckConstraint("monto_garantia >= 0.00", name="chk_contrato_garantia"),
        CheckConstraint("costo_km_excedente >= 0.00", name="chk_contrato_costo_km"),
        CheckConstraint(
            "estado IN ('ACTIVO', 'EN_INSPECCION', 'EN_LIQUIDACION', 'LIQUIDADO', 'ANULADO')",
            name="chk_contrato_estado",
        ),
    )

    id_contrato: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agencias.id_agencia", ondelete="RESTRICT"), nullable=False
    )
    codigo_contrato: Mapped[str] = mapped_column(String(20), nullable=False)
    id_reserva: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("reservas.id_reserva", ondelete="RESTRICT"),
        unique=True,
        nullable=True,
    )
    id_cliente: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("clientes.id_cliente", ondelete="RESTRICT"), nullable=False
    )
    id_vehiculo: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("vehiculos.id_vehiculo", ondelete="RESTRICT"), nullable=False
    )
    id_cobertura: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("coberturas_seguro.id_cobertura", ondelete="RESTRICT"),
        nullable=False,
    )
    fecha_hora_inicio_pactada: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    fecha_hora_fin_pactada: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    fecha_hora_salida_real: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    kilometraje_salida: Mapped[int] = mapped_column(Integer, nullable=False)
    combustible_salida: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), default=Decimal("1.00"), nullable=False
    )
    tarifa_diaria_aplicada: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    monto_garantia: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    kilometraje_ilimitado: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    limite_km_diario: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    costo_km_excedente: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    estado: Mapped[str] = mapped_column(String(25), default="ACTIVO", nullable=False)
    id_usuario: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuarios.id_usuario", ondelete="RESTRICT"), nullable=False
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    cliente: Mapped[Optional["ClienteORM"]] = relationship("ClienteORM", lazy="joined")
    vehiculo: Mapped[Optional["VehiculoORM"]] = relationship("VehiculoORM", lazy="joined")
    cobertura: Mapped[Optional["CoberturaSeguroORM"]] = relationship(
        "CoberturaSeguroORM", lazy="joined"
    )
    usuario: Mapped[Optional["UsuarioORM"]] = relationship("UsuarioORM", lazy="joined")
    reserva: Mapped[Optional["ReservaORM"]] = relationship("ReservaORM", lazy="joined")
    conductores_adicionales: Mapped[List["ConductorAdicionalORM"]] = relationship(
        "ConductorAdicionalORM",
        back_populates="contrato",
        cascade="all, delete-orphan",
        order_by="ConductorAdicionalORM.id_conductor.asc()",
    )
    pagos: Mapped[List["PagoORM"]] = relationship(
        "PagoORM",
        back_populates="contrato",
        order_by="PagoORM.fecha_hora.asc()",
    )

    def to_domain(self, include_collections: bool = True) -> Contract:
        """Convierte la instancia ORM ``ContratoORM`` al modelo de dominio ``Contract``.

        Args:
            include_collections (bool): Si es ``True``, carga conductores adicionales y pagos.

        Returns:
            Contract: Contrato de alquiler enriquecido con datos de cliente, vehículo y seguro.
        """
        veh_modelo = None
        veh_categoria = None
        if self.vehiculo:
            if self.vehiculo.modelo:
                marca_txt = (
                    self.vehiculo.modelo.marca.nombre
                    if self.vehiculo.modelo.marca
                    else ""
                )
                veh_modelo = f"{marca_txt} {self.vehiculo.modelo.nombre}".strip()
            if self.vehiculo.categoria:
                veh_categoria = self.vehiculo.categoria.nombre

        contract = Contract(
            id_contrato=self.id_contrato,
            tenant_id=self.tenant_id,
            codigo_contrato=self.codigo_contrato,
            id_reserva=self.id_reserva,
            id_cliente=self.id_cliente,
            id_vehiculo=self.id_vehiculo,
            id_cobertura=self.id_cobertura,
            fecha_hora_inicio_pactada=self.fecha_hora_inicio_pactada,
            fecha_hora_fin_pactada=self.fecha_hora_fin_pactada,
            fecha_hora_salida_real=self.fecha_hora_salida_real,
            kilometraje_salida=self.kilometraje_salida,
            combustible_salida=Decimal(str(self.combustible_salida)),
            tarifa_diaria_aplicada=Decimal(str(self.tarifa_diaria_aplicada)),
            monto_garantia=Decimal(str(self.monto_garantia)),
            kilometraje_ilimitado=self.kilometraje_ilimitado,
            limite_km_diario=self.limite_km_diario,
            costo_km_excedente=Decimal(str(self.costo_km_excedente)),
            estado=ContractStatus(self.estado),
            id_usuario=self.id_usuario,
            fecha_creacion=self.fecha_creacion,
            cliente_nombre=(
                f"{self.cliente.nombres} {self.cliente.apellidos}".strip()
                if self.cliente
                else None
            ),
            cliente_identificacion=self.cliente.identificacion if self.cliente else None,
            cliente_telefono=self.cliente.telefono if self.cliente else None,
            vehiculo_placa=self.vehiculo.placa if self.vehiculo else None,
            vehiculo_modelo=veh_modelo,
            vehiculo_categoria=veh_categoria,
            cobertura_nombre=self.cobertura.nombre if self.cobertura else None,
            cobertura_costo_diario=(
                Decimal(str(self.cobertura.costo_diario))
                if self.cobertura and self.cobertura.costo_diario is not None
                else None
            ),
            usuario_nombre=self.usuario.nombre_completo if self.usuario else None,
            reserva_codigo=self.reserva.codigo_reserva if self.reserva else None,
        )

        if include_collections:
            contract.conductores_adicionales = [
                d.to_domain() for d in (self.conductores_adicionales or [])
            ]
            contract.pagos = [p.to_domain() for p in (self.pagos or [])]
        return contract


class ConductorAdicionalORM(Base):
    """Modelo ORM para la tabla multi-tenant ``conductores_adicionales``."""

    __tablename__ = "conductores_adicionales"

    id_conductor: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agencias.id_agencia", ondelete="RESTRICT"), nullable=False
    )
    id_contrato: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("contratos.id_contrato", ondelete="CASCADE"), nullable=False
    )
    nombre_completo: Mapped[str] = mapped_column(String(120), nullable=False)
    identificacion: Mapped[str] = mapped_column(String(30), nullable=False)
    numero_licencia: Mapped[str] = mapped_column(String(40), nullable=False)
    fecha_vencimiento_licencia: Mapped[date] = mapped_column(Date, nullable=False)

    contrato: Mapped[Optional["ContratoORM"]] = relationship(
        "ContratoORM", back_populates="conductores_adicionales"
    )

    def to_domain(self) -> AdditionalDriver:
        """Convierte la instancia ORM ``ConductorAdicionalORM`` al modelo ``AdditionalDriver``.

        Returns:
            AdditionalDriver: Conductor autorizado adicional de dominio.
        """
        return AdditionalDriver(
            id_conductor=self.id_conductor,
            tenant_id=self.tenant_id,
            id_contrato=self.id_contrato,
            nombre_completo=self.nombre_completo,
            identificacion=self.identificacion,
            numero_licencia=self.numero_licencia,
            fecha_vencimiento_licencia=self.fecha_vencimiento_licencia,
        )


# ============================================================================
# 6. MÓDULO DE DEVOLUCIONES Y DAÑOS
# ============================================================================


class DevolucionORM(Base):
    """Modelo ORM para la tabla multi-tenant ``devoluciones``."""

    __tablename__ = "devoluciones"
    __table_args__ = (
        CheckConstraint("kilometraje_retorno >= 0", name="chk_devolucion_km"),
        CheckConstraint(
            "combustible_retorno >= 0.00 AND combustible_retorno <= 1.00",
            name="chk_devolucion_combustible",
        ),
        CheckConstraint("horas_retraso >= 0", name="chk_devolucion_retraso"),
    )

    id_devolucion: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agencias.id_agencia", ondelete="RESTRICT"), nullable=False
    )
    id_contrato: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("contratos.id_contrato", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    fecha_hora_retorno_real: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    kilometraje_retorno: Mapped[int] = mapped_column(Integer, nullable=False)
    combustible_retorno: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
    horas_retraso: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    limpieza_aprobada: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    accesorios_completos: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    observaciones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    id_usuario: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuarios.id_usuario", ondelete="RESTRICT"), nullable=False
    )

    contrato: Mapped[Optional["ContratoORM"]] = relationship("ContratoORM", lazy="joined")
    usuario: Mapped[Optional["UsuarioORM"]] = relationship("UsuarioORM", lazy="joined")
    danios: Mapped[List["DanioORM"]] = relationship(
        "DanioORM",
        back_populates="devolucion",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="DanioORM.id_danio.asc()",
    )

    def to_domain(self) -> ReturnInspection:
        """Convierte la instancia ORM ``DevolucionORM`` al modelo ``ReturnInspection``.

        Returns:
            ReturnInspection: Acta de devolución física con sus averías y datos de contrato.
        """
        c = self.contrato
        cl = c.cliente if c else None
        v = c.vehiculo if c else None
        veh_modelo = None
        if v and v.modelo:
            marca_txt = v.modelo.marca.nombre if v.modelo.marca else ""
            veh_modelo = f"{marca_txt} {v.modelo.nombre}".strip()

        return ReturnInspection(
            id_devolucion=self.id_devolucion,
            tenant_id=self.tenant_id,
            id_contrato=self.id_contrato,
            fecha_hora_retorno_real=self.fecha_hora_retorno_real,
            kilometraje_retorno=self.kilometraje_retorno,
            combustible_retorno=Decimal(str(self.combustible_retorno)),
            horas_retraso=self.horas_retraso,
            limpieza_aprobada=self.limpieza_aprobada,
            accesorios_completos=self.accesorios_completos,
            observaciones=self.observaciones,
            id_usuario=self.id_usuario,
            contrato_codigo=c.codigo_contrato if c else None,
            cliente_nombre=f"{cl.nombres} {cl.apellidos}".strip() if cl else None,
            cliente_identificacion=cl.identificacion if cl else None,
            vehiculo_placa=v.placa if v else None,
            vehiculo_modelo=veh_modelo,
            usuario_nombre=self.usuario.nombre_completo if self.usuario else None,
            kilometraje_salida=c.kilometraje_salida if c else 0,
            combustible_salida=(
                Decimal(str(c.combustible_salida)) if c else Decimal("1.00")
            ),
            fecha_hora_fin_pactada=c.fecha_hora_fin_pactada if c else None,
            tarifa_diaria=(
                Decimal(str(c.tarifa_diaria_aplicada)) if c else Decimal("0.00")
            ),
            danios=[d.to_domain() for d in (self.danios or [])],
        )


class DanioORM(Base):
    """Modelo ORM para la tabla multi-tenant ``danios``."""

    __tablename__ = "danios"
    __table_args__ = (
        CheckConstraint(
            "tipo_danio IN ('RAYON', 'GOLPE', 'ROTURA', 'FALTANTE_PIEZA', 'INTERIOR')",
            name="chk_danio_tipo",
        ),
        CheckConstraint(
            "gravedad IN ('LEVE', 'MODERADO', 'GRAVE')",
            name="chk_danio_gravedad",
        ),
        CheckConstraint("costo_reparacion >= 0.00", name="chk_danio_costo"),
    )

    id_danio: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agencias.id_agencia", ondelete="RESTRICT"), nullable=False
    )
    id_devolucion: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("devoluciones.id_devolucion", ondelete="CASCADE"),
        nullable=False,
    )
    zona_carroceria: Mapped[str] = mapped_column(String(50), nullable=False)
    tipo_danio: Mapped[str] = mapped_column(String(30), nullable=False)
    gravedad: Mapped[str] = mapped_column(String(20), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    costo_reparacion: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )

    devolucion: Mapped[Optional["DevolucionORM"]] = relationship(
        "DevolucionORM", back_populates="danios"
    )

    def to_domain(self) -> Damage:
        """Convierte la instancia ORM ``DanioORM`` al modelo de dominio ``Damage``.

        Returns:
            Damage: Avería o daño físico de dominio.
        """
        return Damage(
            id_danio=self.id_danio,
            tenant_id=self.tenant_id,
            id_devolucion=self.id_devolucion,
            zona_carroceria=self.zona_carroceria,
            tipo_danio=DamageType(self.tipo_danio),
            gravedad=DamageSeverity(self.gravedad),
            descripcion=self.descripcion,
            costo_reparacion=Decimal(str(self.costo_reparacion)),
        )


# ============================================================================
# 7. MÓDULO DE LIQUIDACIONES Y CONTROL FINANCIERO
# ============================================================================


class LiquidacionORM(Base):
    """Modelo ORM para la tabla multi-tenant ``liquidaciones``."""

    __tablename__ = "liquidaciones"
    __table_args__ = (
        CheckConstraint("dias_facturados > 0", name="chk_liq_dias"),
        CheckConstraint("subtotal_renta >= 0.00", name="chk_liq_subtotal"),
        CheckConstraint("cargos_retraso >= 0.00", name="chk_liq_retraso"),
        CheckConstraint("cargos_combustible >= 0.00", name="chk_liq_combustible"),
        CheckConstraint("cargos_km_excedente >= 0.00", name="chk_liq_km"),
        CheckConstraint("cargos_danios >= 0.00", name="chk_liq_danios"),
        CheckConstraint("total_bruto >= 0.00", name="chk_liq_bruto"),
        CheckConstraint("monto_garantia_aplicado >= 0.00", name="chk_liq_garantia"),
        CheckConstraint(
            "estado_liquidacion IN ('PENDIENTE_PAGO', 'CERRADA')",
            name="chk_liq_estado",
        ),
    )

    id_liquidacion: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agencias.id_agencia", ondelete="RESTRICT"), nullable=False
    )
    id_contrato: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("contratos.id_contrato", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    id_devolucion: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("devoluciones.id_devolucion", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    fecha_liquidacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    dias_facturados: Mapped[int] = mapped_column(Integer, nullable=False)
    subtotal_renta: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cargos_retraso: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    cargos_combustible: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    cargos_km_excedente: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    cargos_danios: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    total_bruto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    monto_garantia_aplicado: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    saldo_cliente: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    estado_liquidacion: Mapped[str] = mapped_column(
        String(20), default="CERRADA", nullable=False
    )
    id_usuario: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuarios.id_usuario", ondelete="RESTRICT"), nullable=False
    )

    contrato: Mapped[Optional["ContratoORM"]] = relationship("ContratoORM", lazy="joined")
    usuario: Mapped[Optional["UsuarioORM"]] = relationship("UsuarioORM", lazy="joined")
    pagos: Mapped[List["PagoORM"]] = relationship(
        "PagoORM",
        back_populates="liquidacion",
        lazy="selectin",
        order_by="PagoORM.id_pago.asc()",
    )

    def to_domain(self, include_payments: bool = True) -> Settlement:
        """Convierte la instancia ORM ``LiquidacionORM`` al modelo de dominio ``Settlement``.

        Args:
            include_payments (bool): Si es ``True``, incluye los pagos asociados a la liquidación.

        Returns:
            Settlement: Liquidación financiera final con detalles de contrato y pagos.
        """
        c = self.contrato
        cl = c.cliente if c else None
        v = c.vehiculo if c else None

        settlement = Settlement(
            id_liquidacion=self.id_liquidacion,
            tenant_id=self.tenant_id,
            id_contrato=self.id_contrato,
            id_devolucion=self.id_devolucion,
            fecha_liquidacion=self.fecha_liquidacion,
            dias_facturados=self.dias_facturados,
            subtotal_renta=Decimal(str(self.subtotal_renta)),
            cargos_retraso=Decimal(str(self.cargos_retraso)),
            cargos_combustible=Decimal(str(self.cargos_combustible)),
            cargos_km_excedente=Decimal(str(self.cargos_km_excedente)),
            cargos_danios=Decimal(str(self.cargos_danios)),
            total_bruto=Decimal(str(self.total_bruto)),
            monto_garantia_aplicado=Decimal(str(self.monto_garantia_aplicado)),
            saldo_cliente=Decimal(str(self.saldo_cliente)),
            estado_liquidacion=SettlementStatus(self.estado_liquidacion),
            id_usuario=self.id_usuario,
            contrato_codigo=c.codigo_contrato if c else None,
            cliente_nombre=f"{cl.nombres} {cl.apellidos}".strip() if cl else None,
            vehiculo_placa=v.placa if v else None,
            usuario_nombre=self.usuario.nombre_completo if self.usuario else None,
            monto_garantia_inicial=(
                Decimal(str(c.monto_garantia)) if c else Decimal("0.00")
            ),
        )
        if include_payments:
            settlement.pagos = [p.to_domain() for p in (self.pagos or [])]
        return settlement


class PagoORM(Base):
    """Modelo ORM para la tabla multi-tenant ``pagos``."""

    __tablename__ = "pagos"
    __table_args__ = (
        UniqueConstraint("tenant_id", "codigo_transaccion", name="uq_pagos_tenant_codigo"),
        CheckConstraint(
            "tipo_movimiento IN ('ANTICIPO_RESERVA', 'DEPOSITO_GARANTIA', 'COBRO_LIQUIDACION', 'REEMBOLSO_GARANTIA')",
            name="chk_pago_tipo",
        ),
        CheckConstraint(
            "metodo_pago IN ('EFECTIVO', 'TARJETA_CREDITO', 'TARJETA_DEBITO', 'TRANSFERENCIA')",
            name="chk_pago_metodo",
        ),
        CheckConstraint("monto > 0.00", name="chk_pago_monto"),
    )

    id_pago: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agencias.id_agencia", ondelete="RESTRICT"), nullable=False
    )
    codigo_transaccion: Mapped[str] = mapped_column(String(30), nullable=False)
    id_contrato: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("contratos.id_contrato", ondelete="RESTRICT"), nullable=True
    )
    id_reserva: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("reservas.id_reserva", ondelete="RESTRICT"), nullable=True
    )
    id_liquidacion: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("liquidaciones.id_liquidacion", ondelete="RESTRICT"),
        nullable=True,
    )
    tipo_movimiento: Mapped[str] = mapped_column(String(30), nullable=False)
    metodo_pago: Mapped[str] = mapped_column(String(25), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    referencia: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    id_usuario: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuarios.id_usuario", ondelete="RESTRICT"), nullable=False
    )

    contrato: Mapped[Optional["ContratoORM"]] = relationship(
        "ContratoORM", back_populates="pagos"
    )
    liquidacion: Mapped[Optional["LiquidacionORM"]] = relationship(
        "LiquidacionORM", back_populates="pagos"
    )
    usuario: Mapped[Optional["UsuarioORM"]] = relationship("UsuarioORM", lazy="joined")

    def to_domain(self) -> Payment:
        """Convierte la instancia ORM ``PagoORM`` al modelo de dominio ``Payment``.

        Returns:
            Payment: Movimiento financiero de caja de dominio.
        """
        return Payment(
            id_pago=self.id_pago,
            tenant_id=self.tenant_id,
            codigo_transaccion=self.codigo_transaccion,
            id_contrato=self.id_contrato,
            id_reserva=self.id_reserva,
            id_liquidacion=self.id_liquidacion,
            tipo_movimiento=PaymentType(self.tipo_movimiento),
            metodo_pago=PaymentMethod(self.metodo_pago),
            monto=Decimal(str(self.monto)),
            fecha_hora=self.fecha_hora,
            referencia=self.referencia,
            id_usuario=self.id_usuario,
            usuario_nombre=self.usuario.nombre_completo if self.usuario else None,
        )


# ============================================================================
# 8. MÓDULO DE MANTENIMIENTO
# ============================================================================


class MantenimientoORM(Base):
    """Modelo ORM para la tabla multi-tenant ``mantenimientos``."""

    __tablename__ = "mantenimientos"
    __table_args__ = (
        CheckConstraint(
            "tipo_mantenimiento IN ('PREVENTIVO', 'CORRECTIVO')",
            name="chk_mant_tipo",
        ),
        CheckConstraint("kilometraje_entrada >= 0", name="chk_mant_km"),
        CheckConstraint("costo_total >= 0.00", name="chk_mant_costo"),
        CheckConstraint(
            "estado IN ('EN_TALLER', 'FINALIZADO', 'CANCELADO')",
            name="chk_mant_estado",
        ),
    )

    id_mantenimiento: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agencias.id_agencia", ondelete="RESTRICT"), nullable=False
    )
    id_vehiculo: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("vehiculos.id_vehiculo", ondelete="RESTRICT"), nullable=False
    )
    tipo_mantenimiento: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha_ingreso: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    fecha_salida_estimada: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_salida_real: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    kilometraje_entrada: Mapped[int] = mapped_column(Integer, nullable=False)
    taller_servicio: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion_trabajo: Mapped[str] = mapped_column(Text, nullable=False)
    costo_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    estado: Mapped[str] = mapped_column(String(20), default="EN_TALLER", nullable=False)
    id_usuario: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuarios.id_usuario", ondelete="RESTRICT"), nullable=False
    )

    vehiculo: Mapped[Optional["VehiculoORM"]] = relationship("VehiculoORM", lazy="joined")
    usuario: Mapped[Optional["UsuarioORM"]] = relationship("UsuarioORM", lazy="joined")

    def to_domain(self) -> Maintenance:
        """Convierte la instancia ORM ``MantenimientoORM`` al modelo de dominio ``Maintenance``.

        Returns:
            Maintenance: Orden de trabajo en taller mecánico con datos del vehículo y usuario.
        """
        v = self.vehiculo
        veh_modelo = None
        veh_categoria = None
        if v:
            if v.modelo:
                marca_txt = v.modelo.marca.nombre if v.modelo.marca else ""
                veh_modelo = f"{marca_txt} {v.modelo.nombre}".strip()
            if v.categoria:
                veh_categoria = v.categoria.nombre

        return Maintenance(
            id_mantenimiento=self.id_mantenimiento,
            tenant_id=self.tenant_id,
            id_vehiculo=self.id_vehiculo,
            tipo_mantenimiento=MaintenanceType(self.tipo_mantenimiento),
            fecha_ingreso=self.fecha_ingreso,
            fecha_salida_estimada=self.fecha_salida_estimada,
            fecha_salida_real=self.fecha_salida_real,
            kilometraje_entrada=self.kilometraje_entrada,
            taller_servicio=self.taller_servicio,
            descripcion_trabajo=self.descripcion_trabajo,
            costo_total=Decimal(str(self.costo_total)),
            estado=MaintenanceStatus(self.estado),
            id_usuario=self.id_usuario,
            vehiculo_placa=v.placa if v else None,
            vehiculo_modelo=veh_modelo,
            vehiculo_categoria=veh_categoria,
            vehiculo_kilometraje_actual=v.kilometraje_actual if v else 0,
            km_proximo_mantenimiento_actual=v.km_proximo_mantenimiento if v else 0,
            usuario_nombre=self.usuario.nombre_completo if self.usuario else None,
        )
