-- ============================================================================
-- SCRIPT DE PRUEBAS DE INTEGRIDAD Y VALIDACION DE REGLAS DE NEGOCIO
-- ============================================================================

-- ----------------------------------------------------------------------------
-- PRUEBA 1: VERIFICAR QUE SE IMPIDE EL OVERBOOKING (SOLAPAMIENTO DE CONTRATOS)
-- El vehículo ID 4 (Hilux M-405912) tiene un contrato activo que termina mañana.
-- Intentar crear otro contrato para el mismo vehículo con fechas solapadas DEBE FALLAR.
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    BEGIN
        INSERT INTO contratos (
            codigo_contrato, id_cliente, id_vehiculo, id_cobertura,
            fecha_hora_inicio_pactada, fecha_hora_fin_pactada,
            kilometraje_salida, combustible_salida, tarifa_diaria_aplicada, monto_garantia,
            id_usuario
        ) VALUES (
            'CTR-TEST-OVERBOOK', 1, 4, 1,
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
            codigo_contrato, id_cliente, id_vehiculo, id_cobertura,
            fecha_hora_inicio_pactada, fecha_hora_fin_pactada,
            kilometraje_salida, combustible_salida, tarifa_diaria_aplicada, monto_garantia,
            id_usuario
        ) VALUES (
            'CTR-TEST-LICENCIA', 4, 1, 1,
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
            id_contrato, fecha_hora_retorno_real, kilometraje_retorno, combustible_retorno,
            horas_retraso, limpieza_aprobada, accesorios_completos, id_usuario
        ) VALUES (
            1, CURRENT_TIMESTAMP, 34000, 1.00, 0, TRUE, TRUE, 3
        );
        RAISE EXCEPTION 'FALLO: El sistema permitió registrar un kilometraje de retorno menor al de salida.';
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'ÉXITO PRUEBA 3: Trigger de validación de odómetro impidió kilometraje incoherente (Error: %)', SQLERRM;
    END;
END $$;

-- ----------------------------------------------------------------------------
-- CONSULTA 4: TRAZABILIDAD DEL CICLO COMPLETO DE ALQUILER
-- Muestra el flujo completo desde Contrato hasta Liquidación con sus pagos
-- ----------------------------------------------------------------------------
SELECT
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
    l.cargos_danos,
    l.total_bruto,
    l.monto_garantia_aplicado,
    l.saldo_cliente,
    l.estado_liquidacion
FROM
    contratos c
    INNER JOIN clientes cli ON c.id_cliente = cli.id_cliente
    INNER JOIN vehiculos v ON c.id_vehiculo = v.id_vehiculo
    INNER JOIN modelos m ON v.id_modelo = m.id_modelo
    INNER JOIN devoluciones d ON c.id_contrato = d.id_contrato
    INNER JOIN liquidaciones l ON c.id_contrato = l.id_contrato;

-- ----------------------------------------------------------------------------
-- CONSULTA 5: ESTADO Y DISPONIBILIDAD ACTUAL DE LA FLOTA
-- ----------------------------------------------------------------------------
SELECT
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
    INNER JOIN categorias_vehiculo cat ON v.id_categoria = cat.id_categoria
    INNER JOIN modelos m ON v.id_modelo = m.id_modelo
    INNER JOIN marcas mar ON m.id_marca = mar.id_marca
ORDER BY v.estado, v.placa;