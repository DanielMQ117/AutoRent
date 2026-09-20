"""Repositorio de acceso a datos para Reportes, Estadísticas y Analítica de Negocio (DAL)."""

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, List, Optional

from src.core.logger import get_logger
from src.domain.models import (
    ClientHistoryItem,
    ClientHistorySummary,
    FinancialReportItem,
    FinancialReportSummary,
    FleetUtilizationItem,
    FleetUtilizationSummary,
)
from src.repositories.base_repository import BaseRepository

logger = get_logger(__name__)


class ReportRepository(BaseRepository[Any]):
    """Consultas analíticas consolidadas para inteligencia de negocio y auditoría (Fase 9)."""

    # ------------------------------------------------------------------------
    # RF-34: Reporte Consolidado de Ingresos Financieros y Recaudación
    # ------------------------------------------------------------------------

    def get_financial_report(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        metodo_pago: Optional[str] = None,
        concepto: Optional[str] = None,
        conn: Any = None,
    ) -> FinancialReportSummary:
        """Obtiene las transacciones y consolida los indicadores financieros en el periodo."""
        dt_inicio = datetime.combine(fecha_inicio, time.min)
        dt_fin = datetime.combine(fecha_fin, time.max)

        # 1. Consulta detallada de transacciones
        query_items = """
            SELECT 
                p.id_pago,
                p.codigo_transaccion,
                p.tipo_movimiento,
                CASE 
                    WHEN p.tipo_movimiento = 'ANTICIPO_RESERVA' THEN 'Anticipo de Reserva'
                    WHEN p.tipo_movimiento = 'DEPOSITO_GARANTIA' THEN 'Depósito en Garantía (Fianza)'
                    WHEN p.tipo_movimiento = 'COBRO_LIQUIDACION' THEN 'Cobro de Liquidación / Renta'
                    WHEN p.tipo_movimiento = 'REEMBOLSO_GARANTIA' THEN 'Reembolso de Garantía'
                    ELSE p.tipo_movimiento
                END AS concepto,
                p.metodo_pago,
                p.monto,
                p.fecha_hora,
                p.referencia,
                COALESCE(c.codigo_contrato, r.codigo_reserva, '—') AS contrato_codigo,
                COALESCE(cl.nombres || ' ' || cl.apellidos, cl_r.nombres || ' ' || cl_r.apellidos, '—') AS cliente_nombre,
                u.nombre_completo AS usuario_nombre
            FROM pagos p
            LEFT JOIN contratos c ON p.id_contrato = c.id_contrato
            LEFT JOIN reservas r ON p.id_reserva = r.id_reserva
            LEFT JOIN clientes cl ON c.id_cliente = cl.id_cliente
            LEFT JOIN clientes cl_r ON r.id_cliente = cl_r.id_cliente
            LEFT JOIN usuarios u ON p.id_usuario = u.id_usuario
            WHERE p.fecha_hora >= %s AND p.fecha_hora <= %s
        """
        params: list[Any] = [dt_inicio, dt_fin]

        if metodo_pago and metodo_pago.upper() != "TODOS":
            query_items += " AND p.metodo_pago = %s"
            params.append(metodo_pago.upper())

        if concepto and concepto.upper() != "TODOS":
            query_items += " AND p.tipo_movimiento = %s"
            params.append(concepto.upper())

        query_items += " ORDER BY p.fecha_hora DESC;"

        rows = self.execute_query(query_items, tuple(params), conn=conn)

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

        # 2. Consultas agregadas de resumen (KPIs)
        # Ingresos totales por cobros (entradas de dinero)
        query_inflows = """
            SELECT COALESCE(SUM(monto), 0)
            FROM pagos
            WHERE fecha_hora >= %s AND fecha_hora <= %s
              AND tipo_movimiento IN ('ANTICIPO_RESERVA', 'DEPOSITO_GARANTIA', 'COBRO_LIQUIDACION');
        """
        val_inflows = self.execute_scalar(query_inflows, (dt_inicio, dt_fin), conn=conn) or Decimal("0.00")
        total_facturado = Decimal(str(val_inflows))

        # Reembolsos efectuados (salidas a clientes por garantía devuelta)
        query_refunds = """
            SELECT COALESCE(SUM(monto), 0)
            FROM pagos
            WHERE fecha_hora >= %s AND fecha_hora <= %s
              AND tipo_movimiento = 'REEMBOLSO_GARANTIA';
        """
        val_refunds = self.execute_scalar(query_refunds, (dt_inicio, dt_fin), conn=conn) or Decimal("0.00")
        reembolsos_garantia = Decimal(str(val_refunds))

        # Renta base y penalizaciones desde liquidaciones cerradas en el periodo
        query_liq = """
            SELECT 
                COALESCE(SUM(subtotal_renta), 0) AS renta,
                COALESCE(SUM(cargos_retraso + cargos_combustible + cargos_km_excedente + cargos_danios), 0) AS penalizaciones
            FROM liquidaciones
            WHERE fecha_liquidacion >= %s AND fecha_liquidacion <= %s;
        """
        liq_row = self.execute_query_one(query_liq, (dt_inicio, dt_fin), conn=conn) or {}
        ingresos_renta = Decimal(str(liq_row.get("renta") or "0.00"))
        ingresos_penalizaciones = Decimal(str(liq_row.get("penalizaciones") or "0.00"))

        # Gastos operativos en taller mecánico (órdenes finalizadas en el periodo)
        query_workshop = """
            SELECT COALESCE(SUM(costo_total), 0)
            FROM mantenimientos
            WHERE fecha_ingreso >= %s AND fecha_ingreso <= %s
              AND estado = 'FINALIZADO';
        """
        val_workshop = self.execute_scalar(query_workshop, (dt_inicio, dt_fin), conn=conn) or Decimal("0.00")
        gastos_mantenimiento = Decimal(str(val_workshop))

        # Ingreso neto y métricas derivadas
        ingreso_neto = total_facturado - reembolsos_garantia - gastos_mantenimiento
        total_trx = len(items)
        ticket_promedio = (total_facturado / total_trx) if total_trx > 0 else Decimal("0.00")

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

    # ------------------------------------------------------------------------
    # RF-35: Reporte de Utilización, Tasa de Ocupación y Rendimiento de Flota
    # ------------------------------------------------------------------------

    def get_fleet_utilization_report(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        id_categoria: Optional[int] = None,
        search: Optional[str] = None,
        conn: Any = None,
    ) -> FleetUtilizationSummary:
        """Calcula los días rentados, ingresos, días en taller y tasa de ocupación por vehículo."""
        dt_inicio = datetime.combine(fecha_inicio, time.min)
        dt_fin = datetime.combine(fecha_fin, time.max)
        dias_periodo = max(1, (fecha_fin - fecha_inicio).days + 1)

        # Consulta base de todos los vehículos activos
        query = """
            SELECT 
                v.id_vehiculo,
                v.placa,
                (mar.nombre || ' ' || mo.nombre) AS marca_modelo,
                c.nombre AS categoria,
                v.kilometraje_actual,
                v.estado,
                -- Total de contratos en el rango
                (
                    SELECT COUNT(*)
                    FROM contratos ct
                    WHERE ct.id_vehiculo = v.id_vehiculo
                      AND ct.fecha_hora_inicio_pactada <= %s
                      AND ct.fecha_hora_fin_pactada >= %s
                      AND ct.estado IN ('ACTIVO', 'EN_INSPECCION', 'EN_LIQUIDACION', 'LIQUIDADO')
                ) AS total_contratos,
                -- Días totales alquilado en el periodo
                (
                    SELECT COALESCE(SUM(
                        GREATEST(1, DATE_PART('day', 
                            LEAST(ct.fecha_hora_fin_pactada, %s) - GREATEST(ct.fecha_hora_inicio_pactada, %s)
                        )::INTEGER)
                    ), 0)
                    FROM contratos ct
                    WHERE ct.id_vehiculo = v.id_vehiculo
                      AND ct.fecha_hora_inicio_pactada <= %s
                      AND ct.fecha_hora_fin_pactada >= %s
                      AND ct.estado IN ('ACTIVO', 'EN_INSPECCION', 'EN_LIQUIDACION', 'LIQUIDADO')
                ) AS dias_alquilado,
                -- Ingresos generados por el vehículo
                (
                    SELECT COALESCE(SUM(l.total_bruto), 0)
                    FROM liquidaciones l
                    INNER JOIN contratos ct ON l.id_contrato = ct.id_contrato
                    WHERE ct.id_vehiculo = v.id_vehiculo
                      AND l.fecha_liquidacion >= %s
                      AND l.fecha_liquidacion <= %s
                ) AS ingresos_generados,
                -- Días en taller en el periodo
                (
                    SELECT COALESCE(SUM(
                        GREATEST(1, DATE_PART('day', 
                            LEAST(COALESCE(m.fecha_salida_real, CURRENT_TIMESTAMP), %s) - GREATEST(m.fecha_ingreso, %s)
                        )::INTEGER)
                    ), 0)
                    FROM mantenimientos m
                    WHERE m.id_vehiculo = v.id_vehiculo
                      AND m.fecha_ingreso <= %s
                      AND (m.fecha_salida_real IS NULL OR m.fecha_salida_real >= %s)
                      AND m.estado IN ('EN_TALLER', 'FINALIZADO')
                ) AS dias_taller,
                -- Gastos invertidos en taller
                (
                    SELECT COALESCE(SUM(m.costo_total), 0)
                    FROM mantenimientos m
                    WHERE m.id_vehiculo = v.id_vehiculo
                      AND m.fecha_ingreso >= %s
                      AND m.fecha_ingreso <= %s
                ) AS gastos_taller
            FROM vehiculos v
            INNER JOIN modelos mo ON v.id_modelo = mo.id_modelo
            INNER JOIN marcas mar ON mo.id_marca = mar.id_marca
            INNER JOIN categorias_vehiculo c ON v.id_categoria = c.id_categoria
            WHERE v.activo = TRUE
        """
        params: list[Any] = [
            dt_fin, dt_inicio,
            dt_fin, dt_inicio, dt_fin, dt_inicio,
            dt_inicio, dt_fin,
            dt_fin, dt_inicio, dt_fin, dt_inicio,
            dt_inicio, dt_fin,
        ]

        if id_categoria and id_categoria > 0:
            query += " AND v.id_categoria = %s"
            params.append(id_categoria)

        if search and search.strip():
            query += """
                AND (
                    v.placa ILIKE %s 
                    OR mo.nombre ILIKE %s 
                    OR mar.nombre ILIKE %s
                )
            """
            s = f"%{search.strip()}%"
            params.extend([s, s, s])

        query += " ORDER BY dias_alquilado DESC, v.placa ASC;"

        rows = self.execute_query(query, tuple(params), conn=conn)

        items: List[FleetUtilizationItem] = []
        total_dias_alq_flota = 0
        ingresos_totales = Decimal("0.00")
        gastos_totales = Decimal("0.00")
        veh_mas_rentado = "—"
        max_dias = -1

        for r in rows:
            d_alq = int(r["dias_alquilado"] or 0)
            # Tasa de ocupación unitaria: días alquilado / días del periodo
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
            min(100.0, round((total_dias_alq_flota / capacidad_max_dias) * 100.0, 2))
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

    # ------------------------------------------------------------------------
    # RF-36: Reporte de Historial de Clientes, Siniestralidad y Morosidad
    # ------------------------------------------------------------------------

    def get_client_history_report(
        self,
        filtro_criterio: str = "TODOS",
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
        search: Optional[str] = None,
        conn: Any = None,
    ) -> ClientHistorySummary:
        """Analiza la siniestralidad, daños reportados, gastos acumulados y nivel de riesgo por cliente."""
        query = """
            SELECT 
                cl.id_cliente,
                cl.identificacion,
                (cl.nombres || ' ' || cl.apellidos) AS nombre_completo,
                cl.telefono,
                cl.email,
                cl.estado_cliente,
                -- Total de contratos firmados
                COUNT(DISTINCT ct.id_contrato) AS total_contratos,
                -- Días totales alquilados
                COALESCE(SUM(l.dias_facturados), 0) AS total_dias_alquilados,
                -- Total facturado / desembolsado por el cliente
                COALESCE(SUM(l.total_bruto), 0) AS total_gastado,
                -- Total de penalizaciones cobradas
                COALESCE(SUM(l.cargos_retraso + l.cargos_combustible + l.cargos_km_excedente + l.cargos_danios), 0) AS total_penalizaciones,
                -- Total de averías / daños registrados en devoluciones
                (
                    SELECT COUNT(*)
                    FROM danios d
                    INNER JOIN devoluciones dev ON d.id_devolucion = dev.id_devolucion
                    INNER JOIN contratos c_d ON dev.id_contrato = c_d.id_contrato
                    WHERE c_d.id_cliente = cl.id_cliente
                ) AS total_danos
            FROM clientes cl
            LEFT JOIN contratos ct ON cl.id_cliente = ct.id_cliente
            LEFT JOIN liquidaciones l ON ct.id_contrato = l.id_contrato
            WHERE 1=1
        """
        params: list[Any] = []

        if fecha_inicio and fecha_fin:
            dt_inicio = datetime.combine(fecha_inicio, time.min)
            dt_fin = datetime.combine(fecha_fin, time.max)
            query += " AND (ct.fecha_creacion IS NULL OR (ct.fecha_creacion >= %s AND ct.fecha_creacion <= %s))"
            params.extend([dt_inicio, dt_fin])

        if search and search.strip():
            query += """
                AND (
                    cl.identificacion ILIKE %s
                    OR cl.nombres ILIKE %s
                    OR cl.apellidos ILIKE %s
                    OR cl.email ILIKE %s
                )
            """
            s = f"%{search.strip()}%"
            params.extend([s, s, s, s])

        query += """
            GROUP BY cl.id_cliente, cl.identificacion, cl.nombres, cl.apellidos, cl.telefono, cl.email, cl.estado_cliente
            ORDER BY total_contratos DESC, total_gastado DESC;
        """

        rows = self.execute_query(query, tuple(params), conn=conn)

        items: List[ClientHistoryItem] = []
        clientes_frecuentes = 0
        clientes_con_siniestros = 0
        clientes_alto_riesgo = 0

        for r in rows:
            contratos = int(r["total_contratos"] or 0)
            danos = int(r["total_danos"] or 0)
            penalizaciones = Decimal(str(r["total_penalizaciones"] or "0.00"))
            estado = r["estado_cliente"]

            # Algoritmo de cálculo de nivel de riesgo crediticio y operativo
            if estado in ("MOROSO", "VETADO") or danos >= 2:
                nivel_riesgo = "ALTO"
            elif danos == 1 or penalizaciones > Decimal("100.00"):
                nivel_riesgo = "MEDIO"
            else:
                nivel_riesgo = "BAJO"

            # Filtros por criterio de segmentación
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
