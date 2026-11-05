"""Repositorio ORM de acceso a datos para Reportes, Estadísticas y Analítica de Negocio (SQLAlchemy 2.0)."""

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, List, Optional

from sqlalchemy import Integer, and_, case, cast, func, literal, or_, select
from sqlalchemy.orm import aliased

from src.core.logger import get_logger
from src.database.orm_models import (
    CategoriaVehiculoORM,
    ClienteORM,
    ContratoORM,
    DanioORM,
    DevolucionORM,
    LiquidacionORM,
    MantenimientoORM,
    MarcaORM,
    ModeloORM,
    PagoORM,
    ReservaORM,
    UsuarioORM,
    VehiculoORM,
)
from src.domain.models import (
    ClientHistoryItem,
    ClientHistorySummary,
    FinancialReportItem,
    FinancialReportSummary,
    FleetUtilizationItem,
    FleetUtilizationSummary,
)
from src.repositories.orm.base_orm_repository import BaseORMRepository

logger = get_logger(__name__)


class ReportORMRepository(BaseORMRepository[Any]):
    """Consultas analíticas consolidadas mediante SQLAlchemy 2.0 ORM para inteligencia de negocio (Fase 9)."""

    def get_financial_report(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        metodo_pago: Optional[str] = None,
        concepto: Optional[str] = None,
        conn: Any = None,
    ) -> FinancialReportSummary:
        """Obtiene las transacciones y consolida los indicadores financieros en el periodo (RF-34).

        Args:
            fecha_inicio (date): Fecha de inicio del reporte.
            fecha_fin (date): Fecha de corte final del reporte.
            metodo_pago (Optional[str]): Filtro opcional por método de pago (o ``TODOS``).
            concepto (Optional[str]): Filtro opcional por tipo de movimiento (o ``TODOS``).
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            FinancialReportSummary: Resumen consolidado financiero y lista detallada de movimientos.
        """
        dt_inicio = datetime.combine(fecha_inicio, time.min)
        dt_fin = datetime.combine(fecha_fin, time.max)
        tenant_id = self.current_tenant_id

        with self.session_scope(conn) as s:
            cl_ctr = aliased(ClienteORM)
            cl_res = aliased(ClienteORM)

            concepto_expr = case(
                (PagoORM.tipo_movimiento == "ANTICIPO_RESERVA", "Anticipo de Reserva"),
                (
                    PagoORM.tipo_movimiento == "DEPOSITO_GARANTIA",
                    "Depósito en Garantía (Fianza)",
                ),
                (
                    PagoORM.tipo_movimiento == "COBRO_LIQUIDACION",
                    "Cobro de Liquidación / Renta",
                ),
                (PagoORM.tipo_movimiento == "REEMBOLSO_GARANTIA", "Reembolso de Garantía"),
                else_=PagoORM.tipo_movimiento,
            ).label("concepto")

            contrato_codigo_expr = func.coalesce(
                ContratoORM.codigo_contrato, ReservaORM.codigo_reserva, literal("—")
            ).label("contrato_codigo")

            cliente_nombre_expr = func.coalesce(
                cl_ctr.nombres + literal(" ") + cl_ctr.apellidos,
                cl_res.nombres + literal(" ") + cl_res.apellidos,
                literal("—"),
            ).label("cliente_nombre")

            stmt_items = (
                select(
                    PagoORM.id_pago,
                    PagoORM.codigo_transaccion,
                    PagoORM.tipo_movimiento,
                    concepto_expr,
                    PagoORM.metodo_pago,
                    PagoORM.monto,
                    PagoORM.fecha_hora,
                    PagoORM.referencia,
                    contrato_codigo_expr,
                    cliente_nombre_expr,
                    UsuarioORM.nombre_completo.label("usuario_nombre"),
                )
                .select_from(PagoORM)
                .outerjoin(ContratoORM, PagoORM.id_contrato == ContratoORM.id_contrato)
                .outerjoin(ReservaORM, PagoORM.id_reserva == ReservaORM.id_reserva)
                .outerjoin(cl_ctr, ContratoORM.id_cliente == cl_ctr.id_cliente)
                .outerjoin(cl_res, ReservaORM.id_cliente == cl_res.id_cliente)
                .outerjoin(UsuarioORM, PagoORM.id_usuario == UsuarioORM.id_usuario)
                .where(
                    PagoORM.tenant_id == tenant_id,
                    PagoORM.fecha_hora >= dt_inicio,
                    PagoORM.fecha_hora <= dt_fin,
                )
            )

            if metodo_pago and metodo_pago.upper() != "TODOS":
                stmt_items = stmt_items.where(PagoORM.metodo_pago == metodo_pago.upper())

            if concepto and concepto.upper() != "TODOS":
                stmt_items = stmt_items.where(PagoORM.tipo_movimiento == concepto.upper())

            stmt_items = stmt_items.order_by(PagoORM.fecha_hora.desc())
            rows = s.execute(stmt_items).mappings().all()

            items: List[FinancialReportItem] = [
                FinancialReportItem(
                    id_pago=r["id_pago"],
                    codigo_transaccion=r["codigo_transaccion"],
                    tipo_movimiento=r["tipo_movimiento"],
                    concepto=r["concepto"],
                    metodo_pago=r["metodo_pago"],
                    monto=Decimal(str(r["monto"])),
                    fecha_hora=r["fecha_hora"],
                    referencia=r.get("referencia"),
                    contrato_codigo=r.get("contrato_codigo"),
                    cliente_nombre=r.get("cliente_nombre"),
                    usuario_nombre=r.get("usuario_nombre"),
                )
                for r in rows
            ]

            stmt_inflows = select(func.coalesce(func.sum(PagoORM.monto), 0)).where(
                PagoORM.tenant_id == tenant_id,
                PagoORM.fecha_hora >= dt_inicio,
                PagoORM.fecha_hora <= dt_fin,
                PagoORM.tipo_movimiento.in_(
                    ["ANTICIPO_RESERVA", "DEPOSITO_GARANTIA", "COBRO_LIQUIDACION"]
                ),
            )
            val_inflows = s.execute(stmt_inflows).scalar() or Decimal("0.00")
            total_facturado = Decimal(str(val_inflows))

            stmt_refunds = select(func.coalesce(func.sum(PagoORM.monto), 0)).where(
                PagoORM.tenant_id == tenant_id,
                PagoORM.fecha_hora >= dt_inicio,
                PagoORM.fecha_hora <= dt_fin,
                PagoORM.tipo_movimiento == "REEMBOLSO_GARANTIA",
            )
            val_refunds = s.execute(stmt_refunds).scalar() or Decimal("0.00")
            reembolsos_garantia = Decimal(str(val_refunds))

            stmt_liq = select(
                func.coalesce(func.sum(LiquidacionORM.subtotal_renta), 0).label("renta"),
                func.coalesce(
                    func.sum(
                        LiquidacionORM.cargos_retraso
                        + LiquidacionORM.cargos_combustible
                        + LiquidacionORM.cargos_km_excedente
                        + LiquidacionORM.cargos_danios
                    ),
                    0,
                ).label("penalizaciones"),
            ).where(
                LiquidacionORM.tenant_id == tenant_id,
                LiquidacionORM.fecha_liquidacion >= dt_inicio,
                LiquidacionORM.fecha_liquidacion <= dt_fin,
            )
            liq_row = s.execute(stmt_liq).mappings().first() or {}
            ingresos_renta = Decimal(str(liq_row.get("renta") or "0.00"))
            ingresos_penalizaciones = Decimal(str(liq_row.get("penalizaciones") or "0.00"))

            stmt_workshop = select(
                func.coalesce(func.sum(MantenimientoORM.costo_total), 0)
            ).where(
                MantenimientoORM.tenant_id == tenant_id,
                MantenimientoORM.fecha_ingreso >= dt_inicio,
                MantenimientoORM.fecha_ingreso <= dt_fin,
                MantenimientoORM.estado == "FINALIZADO",
            )
            val_workshop = s.execute(stmt_workshop).scalar() or Decimal("0.00")
            gastos_mantenimiento = Decimal(str(val_workshop))

            ingreso_neto = total_facturado - reembolsos_garantia - gastos_mantenimiento
            total_trx = len(items)
            ticket_promedio = (
                (total_facturado / total_trx) if total_trx > 0 else Decimal("0.00")
            )

            return FinancialReportSummary(
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                total_facturado=total_facturado,
                ingresos_renta=ingresos_renta,
                ingresos_seguros=Decimal("0.00"),
                ingresos_penalizaciones=ingresos_penalizaciones,
                reembolsos_garantia=reembolsos_garantia,
                gastos_mantenimiento=gastos_mantenimiento,
                ingreso_neto=ingreso_neto,
                total_transacciones=total_trx,
                ticket_promedio=ticket_promedio.quantize(Decimal("0.01")),
                items=items,
            )

    def get_fleet_utilization_report(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        id_categoria: Optional[int] = None,
        search: Optional[str] = None,
        conn: Any = None,
    ) -> FleetUtilizationSummary:
        """Calcula los días rentados, ingresos, días en taller y tasa de ocupación por vehículo (RF-35).

        Args:
            fecha_inicio (date): Fecha inicial del período de análisis.
            fecha_fin (date): Fecha final del período de análisis.
            id_categoria (Optional[int]): Filtro opcional por categoría vehicular.
            search (Optional[str]): Filtro de búsqueda por placa, marca o modelo.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            FleetUtilizationSummary: Resumen analítico de productividad de la flota y detalle por unidad.
        """
        dt_inicio = datetime.combine(fecha_inicio, time.min)
        dt_fin = datetime.combine(fecha_fin, time.max)
        dias_periodo = max(1, (fecha_fin - fecha_inicio).days + 1)
        tenant_id = self.current_tenant_id

        with self.session_scope(conn) as s:
            ct = aliased(ContratoORM)
            ct_dias = aliased(ContratoORM)
            ct_ing = aliased(ContratoORM)
            l_ing = aliased(LiquidacionORM)
            m_dias = aliased(MantenimientoORM)
            m_gastos = aliased(MantenimientoORM)

            sub_total_contratos = (
                select(func.count())
                .select_from(ct)
                .where(
                    ct.id_vehiculo == VehiculoORM.id_vehiculo,
                    ct.tenant_id == VehiculoORM.tenant_id,
                    ct.fecha_hora_inicio_pactada <= dt_fin,
                    ct.fecha_hora_fin_pactada >= dt_inicio,
                    ct.estado.in_(
                        ["ACTIVO", "EN_INSPECCION", "EN_LIQUIDACION", "LIQUIDADO"]
                    ),
                )
                .correlate(VehiculoORM)
                .scalar_subquery()
            )

            sub_dias_alquilado = (
                select(
                    func.coalesce(
                        func.sum(
                            func.greatest(
                                1,
                                cast(
                                    func.date_part(
                                        "day",
                                        func.least(ct_dias.fecha_hora_fin_pactada, dt_fin)
                                        - func.greatest(
                                            ct_dias.fecha_hora_inicio_pactada, dt_inicio
                                        ),
                                    ),
                                    Integer,
                                ),
                            )
                        ),
                        0,
                    )
                )
                .select_from(ct_dias)
                .where(
                    ct_dias.id_vehiculo == VehiculoORM.id_vehiculo,
                    ct_dias.tenant_id == VehiculoORM.tenant_id,
                    ct_dias.fecha_hora_inicio_pactada <= dt_fin,
                    ct_dias.fecha_hora_fin_pactada >= dt_inicio,
                    ct_dias.estado.in_(
                        ["ACTIVO", "EN_INSPECCION", "EN_LIQUIDACION", "LIQUIDADO"]
                    ),
                )
                .correlate(VehiculoORM)
                .scalar_subquery()
            )

            sub_ingresos_generados = (
                select(func.coalesce(func.sum(l_ing.total_bruto), 0))
                .select_from(l_ing)
                .join(ct_ing, l_ing.id_contrato == ct_ing.id_contrato)
                .where(
                    ct_ing.id_vehiculo == VehiculoORM.id_vehiculo,
                    l_ing.tenant_id == VehiculoORM.tenant_id,
                    l_ing.fecha_liquidacion >= dt_inicio,
                    l_ing.fecha_liquidacion <= dt_fin,
                )
                .correlate(VehiculoORM)
                .scalar_subquery()
            )

            sub_dias_taller = (
                select(
                    func.coalesce(
                        func.sum(
                            func.greatest(
                                1,
                                cast(
                                    func.date_part(
                                        "day",
                                        func.least(
                                            func.coalesce(
                                                m_dias.fecha_salida_real,
                                                func.current_timestamp(),
                                            ),
                                            dt_fin,
                                        )
                                        - func.greatest(m_dias.fecha_ingreso, dt_inicio),
                                    ),
                                    Integer,
                                ),
                            )
                        ),
                        0,
                    )
                )
                .select_from(m_dias)
                .where(
                    m_dias.id_vehiculo == VehiculoORM.id_vehiculo,
                    m_dias.tenant_id == VehiculoORM.tenant_id,
                    m_dias.fecha_ingreso <= dt_fin,
                    or_(
                        m_dias.fecha_salida_real.is_(None),
                        m_dias.fecha_salida_real >= dt_inicio,
                    ),
                    m_dias.estado.in_(["EN_TALLER", "FINALIZADO"]),
                )
                .correlate(VehiculoORM)
                .scalar_subquery()
            )

            sub_gastos_taller = (
                select(func.coalesce(func.sum(m_gastos.costo_total), 0))
                .select_from(m_gastos)
                .where(
                    m_gastos.id_vehiculo == VehiculoORM.id_vehiculo,
                    m_gastos.tenant_id == VehiculoORM.tenant_id,
                    m_gastos.fecha_ingreso >= dt_inicio,
                    m_gastos.fecha_ingreso <= dt_fin,
                )
                .correlate(VehiculoORM)
                .scalar_subquery()
            )

            dias_alq_col = sub_dias_alquilado.label("dias_alquilado")
            stmt = (
                select(
                    VehiculoORM.id_vehiculo,
                    VehiculoORM.placa,
                    (MarcaORM.nombre + literal(" ") + ModeloORM.nombre).label(
                        "marca_modelo"
                    ),
                    CategoriaVehiculoORM.nombre.label("categoria"),
                    VehiculoORM.kilometraje_actual,
                    VehiculoORM.estado,
                    sub_total_contratos.label("total_contratos"),
                    dias_alq_col,
                    sub_ingresos_generados.label("ingresos_generados"),
                    sub_dias_taller.label("dias_taller"),
                    sub_gastos_taller.label("gastos_taller"),
                )
                .select_from(VehiculoORM)
                .join(ModeloORM, VehiculoORM.id_modelo == ModeloORM.id_modelo)
                .join(MarcaORM, ModeloORM.id_marca == MarcaORM.id_marca)
                .join(
                    CategoriaVehiculoORM,
                    VehiculoORM.id_categoria == CategoriaVehiculoORM.id_categoria,
                )
                .where(
                    VehiculoORM.tenant_id == tenant_id,
                    VehiculoORM.activo.is_(True),
                )
            )

            if id_categoria and id_categoria > 0:
                stmt = stmt.where(VehiculoORM.id_categoria == id_categoria)

            if search and search.strip():
                term = f"%{search.strip()}%"
                stmt = stmt.where(
                    or_(
                        VehiculoORM.placa.ilike(term),
                        ModeloORM.nombre.ilike(term),
                        MarcaORM.nombre.ilike(term),
                    )
                )

            stmt = stmt.order_by(dias_alq_col.desc(), VehiculoORM.placa.asc())
            rows = s.execute(stmt).mappings().all()

            items: List[FleetUtilizationItem] = []
            total_dias_alq_flota = 0
            ingresos_totales = Decimal("0.00")
            gastos_totales = Decimal("0.00")
            veh_mas_rentado = "—"
            max_dias = -1

            for r in rows:
                d_alq = int(r["dias_alquilado"] or 0)
                tasa_unit = min(100.0, round((d_alq / dias_periodo) * 100.0, 2))
                ingresos = Decimal(str(r["ingresos_generados"] or "0.00"))
                gastos = Decimal(str(r["gastos_taller"] or "0.00"))

                total_dias_alq_flota += d_alq
                ingresos_totales += ingresos
                gastos_totales += gastos

                if d_alq > max_dias and d_alq > 0:
                    max_dias = d_alq
                    veh_mas_rentado = f"{r['placa']} ({r['marca_modelo']})"

                items.append(
                    FleetUtilizationItem(
                        id_vehiculo=r["id_vehiculo"],
                        placa=r["placa"],
                        marca_modelo=r["marca_modelo"],
                        categoria=r["categoria"],
                        total_contratos=int(r["total_contratos"] or 0),
                        dias_alquilado=d_alq,
                        tasa_ocupacion_pct=tasa_unit,
                        ingresos_generados=ingresos,
                        dias_taller=int(r["dias_taller"] or 0),
                        gastos_taller=gastos,
                        kilometraje_actual=int(r["kilometraje_actual"] or 0),
                        estado_actual=r["estado"],
                    )
                )

            total_vehs = len(items)
            capacidad_max_dias = total_vehs * dias_periodo
            tasa_ocupacion_prom = (
                min(
                    100.0,
                    round((total_dias_alq_flota / capacidad_max_dias) * 100.0, 2),
                )
                if capacidad_max_dias > 0
                else 0.0
            )

            return FleetUtilizationSummary(
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                dias_periodo=dias_periodo,
                total_vehiculos=total_vehs,
                total_dias_alquilados=total_dias_alq_flota,
                tasa_ocupacion_promedio=tasa_ocupacion_prom,
                ingresos_totales_flota=ingresos_totales,
                gastos_totales_taller=gastos_totales,
                vehiculo_mas_rentado=veh_mas_rentado,
                items=items,
            )

    def get_client_history_report(
        self,
        filtro_criterio: str = "TODOS",
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
        search: Optional[str] = None,
        conn: Any = None,
    ) -> ClientHistorySummary:
        """Analiza la siniestralidad, daños reportados, gastos acumulados y nivel de riesgo por cliente (RF-36).

        Args:
            filtro_criterio (str): Criterio de segmentación (``TODOS``, ``FRECUENTES``, ``CON_SINIESTROS``, ``RIESGO_ALTO``).
            fecha_inicio (Optional[date]): Fecha inicial opcional para filtrar contratos.
            fecha_fin (Optional[date]): Fecha final opcional para filtrar contratos.
            search (Optional[str]): Búsqueda por identificación, nombres, apellidos o email.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            ClientHistorySummary: Resumen analítico de comportamiento crediticio y listado de clientes.
        """
        with self.session_scope(conn) as s:
            d_sub = aliased(DanioORM)
            dev_sub = aliased(DevolucionORM)
            c_d_sub = aliased(ContratoORM)

            sub_total_danos = (
                select(func.count())
                .select_from(d_sub)
                .join(dev_sub, d_sub.id_devolucion == dev_sub.id_devolucion)
                .join(c_d_sub, dev_sub.id_contrato == c_d_sub.id_contrato)
                .where(
                    c_d_sub.id_cliente == ClienteORM.id_cliente,
                    d_sub.tenant_id == ClienteORM.tenant_id,
                )
                .correlate(ClienteORM)
                .scalar_subquery()
            )

            total_contratos_col = func.count(
                func.distinct(ContratoORM.id_contrato)
            ).label("total_contratos")
            total_gastado_col = func.coalesce(
                func.sum(LiquidacionORM.total_bruto), 0
            ).label("total_gastado")

            stmt = (
                select(
                    ClienteORM.id_cliente,
                    ClienteORM.identificacion,
                    (ClienteORM.nombres + literal(" ") + ClienteORM.apellidos).label(
                        "nombre_completo"
                    ),
                    ClienteORM.telefono,
                    ClienteORM.email,
                    ClienteORM.estado_cliente,
                    total_contratos_col,
                    func.coalesce(func.sum(LiquidacionORM.dias_facturados), 0).label(
                        "total_dias_alquilados"
                    ),
                    total_gastado_col,
                    func.coalesce(
                        func.sum(
                            LiquidacionORM.cargos_retraso
                            + LiquidacionORM.cargos_combustible
                            + LiquidacionORM.cargos_km_excedente
                            + LiquidacionORM.cargos_danios
                        ),
                        0,
                    ).label("total_penalizaciones"),
                    sub_total_danos.label("total_danos"),
                )
                .select_from(ClienteORM)
                .outerjoin(
                    ContratoORM,
                    and_(
                        ClienteORM.id_cliente == ContratoORM.id_cliente,
                        ContratoORM.tenant_id == ClienteORM.tenant_id,
                    ),
                )
                .outerjoin(
                    LiquidacionORM,
                    and_(
                        ContratoORM.id_contrato == LiquidacionORM.id_contrato,
                        LiquidacionORM.tenant_id == ClienteORM.tenant_id,
                    ),
                )
                .where(ClienteORM.tenant_id == self.current_tenant_id)
            )

            if fecha_inicio and fecha_fin:
                dt_inicio = datetime.combine(fecha_inicio, time.min)
                dt_fin = datetime.combine(fecha_fin, time.max)
                stmt = stmt.where(
                    or_(
                        ContratoORM.fecha_creacion.is_(None),
                        and_(
                            ContratoORM.fecha_creacion >= dt_inicio,
                            ContratoORM.fecha_creacion <= dt_fin,
                        ),
                    )
                )

            if search and search.strip():
                term = f"%{search.strip()}%"
                stmt = stmt.where(
                    or_(
                        ClienteORM.identificacion.ilike(term),
                        ClienteORM.nombres.ilike(term),
                        ClienteORM.apellidos.ilike(term),
                        ClienteORM.email.ilike(term),
                    )
                )

            stmt = stmt.group_by(
                ClienteORM.id_cliente,
                ClienteORM.identificacion,
                ClienteORM.nombres,
                ClienteORM.apellidos,
                ClienteORM.telefono,
                ClienteORM.email,
                ClienteORM.estado_cliente,
            ).order_by(total_contratos_col.desc(), total_gastado_col.desc())

            rows = s.execute(stmt).mappings().all()

            items: List[ClientHistoryItem] = []
            clientes_frecuentes = 0
            clientes_con_siniestros = 0
            clientes_alto_riesgo = 0

            for r in rows:
                contratos = int(r["total_contratos"] or 0)
                danos = int(r["total_danos"] or 0)
                penalizaciones = Decimal(str(r["total_penalizaciones"] or "0.00"))
                estado = r["estado_cliente"]

                if estado in ("MOROSO", "VETADO") or danos >= 2:
                    nivel_riesgo = "ALTO"
                elif danos == 1 or penalizaciones > Decimal("100.00"):
                    nivel_riesgo = "MEDIO"
                else:
                    nivel_riesgo = "BAJO"

                if filtro_criterio == "FRECUENTES" and contratos < 2:
                    continue
                if filtro_criterio == "CON_SINIESTROS" and danos <= 0:
                    continue
                if filtro_criterio == "RIESGO_ALTO" and nivel_riesgo != "ALTO":
                    continue

                if contratos >= 2:
                    clientes_frecuentes += 1
                if danos > 0:
                    clientes_con_siniestros += 1
                if nivel_riesgo == "ALTO":
                    clientes_alto_riesgo += 1

                items.append(
                    ClientHistoryItem(
                        id_cliente=r["id_cliente"],
                        identificacion=r["identificacion"],
                        nombre_completo=r["nombre_completo"],
                        telefono=r["telefono"],
                        email=r["email"],
                        estado_cliente=estado,
                        total_contratos=contratos,
                        total_gastado=Decimal(str(r["total_gastado"] or "0.00")),
                        total_dias_alquilados=int(r["total_dias_alquilados"] or 0),
                        total_danos_reportados=danos,
                        total_cargos_penalizaciones=penalizaciones,
                        nivel_riesgo=nivel_riesgo,
                    )
                )

            return ClientHistorySummary(
                total_clientes_analizados=len(items),
                clientes_frecuentes=clientes_frecuentes,
                clientes_con_siniestros=clientes_con_siniestros,
                clientes_alto_riesgo=clientes_alto_riesgo,
                items=items,
            )
