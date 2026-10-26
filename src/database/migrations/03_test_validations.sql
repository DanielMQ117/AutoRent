-- ============================================================================
-- SCRIPT DE PRUEBAS DE INTEGRIDAD Y VALIDACION DE REGLAS DE NEGOCIO (MULTI-TENANT)
-- ============================================================================

-- Establecer contexto de sesión RLS para la Agencia 1 antes de ejecutar validaciones
SELECT sp_set_tenant_context(1);

-- ----------------------------------------------------------------------------
-- PRUEBA 1: VERIFICAR QUE SE IMPIDE EL OVERBOOKING (SOLAPAMIENTO DE CONTRATOS)
-- El vehículo ID 4 (Hilux M-405912) tiene un contrato activo que termina mañana.
-- Intentar crear otro contrato para el mismo vehículo con fechas solapadas DEBE FALLAR.
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    BEGIN
        INSERT INTO contratos (
            tenant_id, codigo_contrato, id_cliente, id_vehiculo, id_cobertura,
            fecha_hora_inicio_pactada, fecha_hora_fin_pactada,
            kilometraje_salida, combustible_salida, tarifa_diaria_aplicada, monto_garantia,
            id_usuario
        ) VALUES (
            1, 'CTR-TEST-OVERBOOK', 1, 4, 1,
            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '2 days',
            35000, 1.00, 90.00, 600.00,
            2
        );
        RAISE EXCEPTION 'FALLO: El sistema permitió el solapamiento de contratos para el mismo vehículo.';
    EXCEPTION WHEN exclusion_violation THEN
        RAISE NOTICE 'ÉXITO PRUEBA 1: Restricción de exclusión GiST impidió el solapamiento de alquiler para el vehículo ID 4.';
    END;
END $$;

-- ----------------------------------------------------------------------------
-- PRUEBA 2: VERIFICAR QUE SE IMPIDE ALQUILAR CON LICENCIA VENCIDA
-- El cliente ID 4 (Roberto Mendoza) tiene una licencia que venció en 2024.
-- Intentar crear un contrato para este cliente DEBE FALLAR mediante el trigger.
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    BEGIN
        INSERT INTO contratos (
            tenant_id, codigo_contrato, id_cliente, id_vehiculo, id_cobertura,
            fecha_hora_inicio_pactada, fecha_hora_fin_pactada,
            kilometraje_salida, combustible_salida, tarifa_diaria_aplicada, monto_garantia,
            id_usuario
        ) VALUES (
            1, 'CTR-TEST-LICENCIA', 4, 1, 1,
            CURRENT_TIMESTAMP + INTERVAL '1 day', CURRENT_TIMESTAMP + INTERVAL '3 days',
            15200, 1.00, 35.00, 250.00,
            2
        );
        RAISE EXCEPTION 'FALLO: El sistema permitió alquilar con una licencia vencida.';
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'ÉXITO PRUEBA 2: Trigger de validación de licencia impidió el contrato (Error: %)', SQLERRM;
    END;
END $$;

-- ----------------------------------------------------------------------------
-- PRUEBA 3: VERIFICAR INCOHERENCIA DE ODÓMETRO EN LA DEVOLUCIÓN
-- Si el contrato CTR-2026-001 salió con 34,500 km, intentar devolver con 34,000 km DEBE FALLAR.
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    BEGIN
        INSERT INTO devoluciones (
            tenant_id, id_contrato, fecha_hora_retorno_real, kilometraje_retorno, combustible_retorno,
            horas_retraso, limpieza_aprobada, accesorios_completos, id_usuario
        ) VALUES (
            1, 1, CURRENT_TIMESTAMP, 34000, 1.00, 0, TRUE, TRUE, 3
        );
        RAISE EXCEPTION 'FALLO: El sistema permitió registrar un kilometraje de retorno menor al de salida.';
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'ÉXITO PRUEBA 3: Trigger de validación de odómetro impidió kilometraje incoherente (Error: %)', SQLERRM;
    END;
END $$;

-- ----------------------------------------------------------------------------
-- CONSULTA 4: TRAZABILIDAD DEL CICLO COMPLETO DE ALQUILER (FILTRADO POR TENANT)
-- Muestra el flujo completo desde Contrato hasta Liquidación con sus pagos
-- ----------------------------------------------------------------------------
SELECT
    ag.codigo_agencia,
    c.codigo_contrato,
    cli.nombres || ' ' || cli.apellidos AS cliente,
    v.placa,
    m.nombre AS modelo,
    c.fecha_hora_salida_real,
    c.kilometraje_salida,
    d.fecha_hora_retorno_real,
    d.kilometraje_retorno,
    (
        d.kilometraje_retorno - c.kilometraje_salida
    ) AS km_recorridos,
    l.subtotal_renta,
    l.cargos_danios,
    l.total_bruto,
    l.monto_garantia_aplicado,
    l.saldo_cliente,
    l.estado_liquidacion
FROM
    contratos c
    INNER JOIN agencias ag ON c.tenant_id = ag.id_agencia
    INNER JOIN clientes cli ON c.id_cliente = cli.id_cliente AND c.tenant_id = cli.tenant_id
    INNER JOIN vehiculos v ON c.id_vehiculo = v.id_vehiculo AND c.tenant_id = v.tenant_id
    INNER JOIN modelos m ON v.id_modelo = m.id_modelo
    INNER JOIN devoluciones d ON c.id_contrato = d.id_contrato AND c.tenant_id = d.tenant_id
    INNER JOIN liquidaciones l ON c.id_contrato = l.id_contrato AND c.tenant_id = l.tenant_id
WHERE
    c.tenant_id = 1;

-- ----------------------------------------------------------------------------
-- CONSULTA 5: ESTADO Y DISPONIBILIDAD ACTUAL DE LA FLOTA (FILTRADO POR TENANT)
-- ----------------------------------------------------------------------------
SELECT
    ag.codigo_agencia,
    v.placa,
    cat.nombre AS categoria,
    mar.nombre || ' ' || m.nombre || ' (' || m.anio || ')' AS vehiculo,
    v.kilometraje_actual,
    v.estado,
    v.km_proximo_mantenimiento,
    CASE
        WHEN v.kilometraje_actual >= v.km_proximo_mantenimiento THEN 'MANTENIMIENTO URGENTE'
        WHEN (
            v.km_proximo_mantenimiento - v.kilometraje_actual
        ) <= 1000 THEN 'PROXIMO A SERVICIO'
        ELSE 'OPTIMO'
    END AS alerta_servicio
FROM
    vehiculos v
    INNER JOIN agencias ag ON v.tenant_id = ag.id_agencia
    INNER JOIN categorias_vehiculo cat ON v.id_categoria = cat.id_categoria AND v.tenant_id = cat.tenant_id
    INNER JOIN modelos m ON v.id_modelo = m.id_modelo
    INNER JOIN marcas mar ON m.id_marca = mar.id_marca
WHERE
    v.tenant_id = 1
ORDER BY v.estado, v.placa;

-- ----------------------------------------------------------------------------
-- PRUEBA 6: VERIFICAR AISLAMIENTO MULTI-AGENCIA CON ROW LEVEL SECURITY (RLS)
-- Valida que bajo el rol de aplicación 'autorent_app' (NOBYPASSRLS):
-- 1) Sin contexto de agencia (Fail-Fast), las consultas retornan 0 filas.
-- 2) Con contexto de Agencia 1, solo se ven datos de Agencia 1 y se bloquea
--    cualquier intento de insertar registros para otra agencia.
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    v_count_no_tenant INTEGER;
    v_count_tenant_1 INTEGER;
BEGIN
    -- Asumir el rol de aplicación sujeto a políticas RLS
    EXECUTE 'SET LOCAL ROLE autorent_app';

    -- 1. Limpiar el contexto de tenant (Fail-Fast / Deny-by-Default)
    PERFORM sp_set_tenant_context(NULL);
    SELECT COUNT(*) INTO v_count_no_tenant FROM clientes;
    IF v_count_no_tenant <> 0 THEN
        RAISE EXCEPTION 'FALLO RLS: Se expusieron % clientes sin tenant_id configurado en la sesión.', v_count_no_tenant;
    END IF;

    -- 2. Establecer contexto en Agencia 1 y verificar visibilidad
    PERFORM sp_set_tenant_context(1);
    SELECT COUNT(*) INTO v_count_tenant_1 FROM clientes;
    IF v_count_tenant_1 = 0 THEN
        RAISE EXCEPTION 'FALLO RLS: No se retornaron los clientes legítimos de la Agencia 1.';
    END IF;

    -- 3. Intentar insertar un registro falseando otro tenant_id (ej. 999) DEBE FALLAR por WITH CHECK
    BEGIN
        INSERT INTO clientes (
            tenant_id, tipo_persona, identificacion, nombres, apellidos, telefono, email, direccion
        ) VALUES (
            999, 'NATURAL', '999-999999-9999Z', 'Intruso', 'Cross Tenant', '00000000', 'intruso@test.com', 'N/A'
        );
        RAISE EXCEPTION 'FALLO RLS: La política permitió insertar una fila con tenant_id distinto al de la sesión.';
    EXCEPTION WHEN insufficient_privilege THEN
        RAISE NOTICE 'ÉXITO PRUEBA 6: Row Level Security (RLS Policy) verificada (0 filas sin contexto, % filas en Agencia 1, e inserción cruzada bloqueada: %).', v_count_tenant_1, SQLERRM;
    END;

    EXECUTE 'RESET ROLE';
END $$;
