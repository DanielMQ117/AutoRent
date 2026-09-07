-- ============================================================================
-- SCRIPT DE DATOS DE PRUEBA Y CARGA INICIAL (SEEDS)
-- ============================================================================

-- 1. Roles del Sistema
INSERT INTO
    roles (nombre, descripcion)
VALUES (
        'ADMINISTRADOR',
        'Acceso total al sistema y configuraciones globales'
    ),
    (
        'AGENTE_VENTAS',
        'Atención en mostrador, reservas, contratos y cobranza'
    ),
    (
        'INSPECTOR_TALLER',
        'Inspecciones físicas de entrega/retorno y control de taller'
    ),
    (
        'GERENTE',
        'Supervisión operativa, reportes ejecutivos y autorizaciones especiales'
    );

-- 2. Usuarios Iniciales (Contraseñas simuladas con hash bcrypt)
INSERT INTO
    usuarios (
        id_rol,
        username,
        password_hash,
        nombre_completo,
        email
    )
VALUES (
        1,
        'admin',
        '$2b$12$e8Yk1O1a6oDk9dFkKzK7ue0OcbHw5B.Qo0U4A5xQ7E7j9XwY3mJ2u',
        'Carlos Fonseca Amador',
        'admin@rentacar.com'
    ),
    (
        2,
        'agente1',
        '$2b$12$e8Yk1O1a6oDk9dFkKzK7ue0OcbHw5B.Qo0U4A5xQ7E7j9XwY3mJ2u',
        'Maria Elena Morales',
        'maria.agente@rentacar.com'
    ),
    (
        3,
        'taller1',
        '$2b$12$e8Yk1O1a6oDk9dFkKzK7ue0OcbHw5B.Qo0U4A5xQ7E7j9XwY3mJ2u',
        'Jorge Gutierrez Lopez',
        'jorge.taller@rentacar.com'
    ),
    (
        4,
        'gerente1',
        '$2b$12$e8Yk1O1a6oDk9dFkKzK7ue0OcbHw5B.Qo0U4A5xQ7E7j9XwY3mJ2u',
        'Sofia Lorente Blandon',
        'sofia.gerente@rentacar.com'
    );

-- 3. Marcas y Modelos
INSERT INTO
    marcas (nombre)
VALUES ('Toyota'),
    ('Hyundai'),
    ('Nissan'),
    ('Kia');

INSERT INTO
    modelos (
        id_marca,
        nombre,
        anio,
        tipo_transmision,
        capacidad_pasajeros
    )
VALUES (
        1,
        'Yaris Sedán',
        2023,
        'AUTOMATICA',
        5
    ),
    (
        1,
        'Hilux 4x4 Doble Cabina',
        2024,
        'MANUAL',
        5
    ),
    (
        1,
        'Corolla',
        2023,
        'AUTOMATICA',
        5
    ),
    (
        2,
        'Tucson',
        2023,
        'AUTOMATICA',
        5
    ),
    (
        2,
        'Grand i10',
        2022,
        'MANUAL',
        5
    ),
    (
        3,
        'Frontier',
        2023,
        'MANUAL',
        5
    ),
    (
        4,
        'Sportage',
        2024,
        'AUTOMATICA',
        5
    );

-- 4. Categorías de Vehículos
INSERT INTO
    categorias_vehiculo (
        nombre,
        descripcion,
        deposito_garantia_sugerido,
        tarifa_base_diaria
    )
VALUES (
        'Económico',
        'Vehículos compactos de bajo consumo de combustible para ciudad',
        250.00,
        35.00
    ),
    (
        'Sedán Intermedio',
        'Vehículos confortables de 4 puertas para viajes ejecutivos',
        350.00,
        50.00
    ),
    (
        'SUV Familiar',
        'Camionetas amplias con tracción y confort para familias',
        500.00,
        75.00
    ),
    (
        'Pickup Trabajo/4x4',
        'Vehículos todo terreno ideales para carga y terrenos difíciles',
        600.00,
        90.00
    );

-- 5. Flota de Vehículos
INSERT INTO
    vehiculos (
        id_modelo,
        id_categoria,
        placa,
        vin,
        color,
        kilometraje_actual,
        nivel_combustible_actual,
        estado,
        km_proximo_mantenimiento
    )
VALUES
    -- Vehículos Disponibles
    (
        1,
        1,
        'M-245890',
        '1HGCR2F83HA001001',
        'Blanco',
        15200,
        1.00,
        'DISPONIBLE',
        20000
    ),
    (
        3,
        2,
        'M-312450',
        '2T1BURHE5HC002002',
        'Plata',
        28400,
        1.00,
        'DISPONIBLE',
        30000
    ),
    (
        4,
        3,
        'M-198765',
        'KM8J33A46LU003003',
        'Gris Oscuro',
        42100,
        1.00,
        'DISPONIBLE',
        45000
    ),
    -- Vehículo Alquilado
    (
        2,
        4,
        'M-405912',
        'MROEB3CD4P0004004',
        'Rojo',
        35000,
        1.00,
        'ALQUILADO',
        40000
    ),
    -- Vehículo en Mantenimiento Preventivo
    (
        5,
        1,
        'M-112233',
        'KMHCT4AE8NU005005',
        'Azul',
        50050,
        0.50,
        'EN_MANTENIMIENTO',
        50000
    );

-- 6. Clientes y Licencias
INSERT INTO
    clientes (
        tipo_persona,
        identificacion,
        nombres,
        apellidos,
        telefono,
        email,
        direccion,
        estado_cliente
    )
VALUES (
        'NATURAL',
        '001-150898-0023K',
        'Ernesto',
        'Cardenal Rivas',
        '+505-8899-1122',
        'ernesto.cardenal@email.com',
        'Colonia Centroamérica, Managua',
        'ACTIVO'
    ),
    (
        'NATURAL',
        '281-200395-0001P',
        'Lucia',
        'Valle Siles',
        '+505-8455-3344',
        'lucia.valle@email.com',
        'Reparto San Juan, Managua',
        'ACTIVO'
    ),
    (
        'JURIDICA',
        'J0310000123456',
        'Constructora del Valle S.A.',
        'Representante: Ing. Gomez',
        '+505-2278-9900',
        'contacto@constructora.com',
        'Km 8.5 Carretera a Masaya',
        'ACTIVO'
    ),
    (
        'NATURAL',
        '001-050490-0044R',
        'Roberto',
        'Mendoza Parrales',
        '+505-8900-7766',
        'roberto.m@email.com',
        'Bello Horizonte, Managua',
        'MOROSO'
    );

INSERT INTO
    licencias_conducir (
        id_cliente,
        numero_licencia,
        categoria_licencia,
        fecha_emision,
        fecha_vencimiento,
        pais_emision
    )
VALUES (
        1,
        'LIC-001150898',
        'CATEGORIA_3',
        '2022-01-15',
        '2027-01-15',
        'Nicaragua'
    ),
    (
        2,
        'LIC-281200395',
        'CATEGORIA_3',
        '2023-05-10',
        '2028-05-10',
        'Nicaragua'
    ),
    (
        3,
        'LIC-001000999',
        'CATEGORIA_4',
        '2021-11-20',
        '2026-11-20',
        'Nicaragua'
    ),
    (
        4,
        'LIC-001050490',
        'CATEGORIA_3',
        '2019-03-10',
        '2024-03-10',
        'Nicaragua'
    );
-- Licencia vencida (para pruebas de validación)

-- 7. Coberturas de Seguro
INSERT INTO
    coberturas_seguro (
        nombre,
        descripcion,
        costo_diario,
        porcentaje_deducible
    )
VALUES (
        'Básico Obligatorio',
        'Cubre responsabilidad civil frente a terceros según ley',
        8.00,
        20.00
    ),
    (
        'Cobertura Amplia',
        'Colisión, robo total y daños a terceros con deducible moderado',
        15.00,
        10.00
    ),
    (
        'Premium Cero Deducible',
        'Protección total ante cualquier daño físico, colisión o rotura sin deducible',
        25.00,
        0.00
    );

-- 8. Caso 1: Reserva Confirmada con Anticipo (Futura)
INSERT INTO
    reservas (
        codigo_reserva,
        id_cliente,
        id_categoria,
        id_vehiculo,
        fecha_hora_inicio,
        fecha_hora_fin,
        monto_anticipo,
        estado,
        id_usuario
    )
VALUES (
        'RES-2026-001',
        1,
        1,
        1,
        CURRENT_TIMESTAMP + INTERVAL '3 days',
        CURRENT_TIMESTAMP + INTERVAL '6 days',
        50.00,
        'CONFIRMADA',
        2
    );

INSERT INTO
    pagos (
        codigo_transaccion,
        id_reserva,
        tipo_movimiento,
        metodo_pago,
        monto,
        referencia,
        id_usuario
    )
VALUES (
        'TRX-ANT-001',
        1,
        'ANTICIPO_RESERVA',
        'TARJETA_CREDITO',
        50.00,
        'AUTH-789456',
        2
    );

-- 9. Caso 2: Contrato Activo en Curso (Vehículo en circulación)
INSERT INTO
    contratos (
        codigo_contrato,
        id_cliente,
        id_vehiculo,
        id_cobertura,
        fecha_hora_inicio_pactada,
        fecha_hora_fin_pactada,
        fecha_hora_salida_real,
        kilometraje_salida,
        combustible_salida,
        tarifa_diaria_aplicada,
        monto_garantia,
        kilometraje_ilimitado,
        estado,
        id_usuario
    )
VALUES (
        'CTR-2026-001',
        2,
        4,
        2,
        CURRENT_TIMESTAMP - INTERVAL '2 days',
        CURRENT_TIMESTAMP + INTERVAL '1 day',
        CURRENT_TIMESTAMP - INTERVAL '2 days',
        34500,
        1.00,
        90.00,
        600.00,
        TRUE,
        'ACTIVO',
        2
    );

INSERT INTO
    pagos (
        codigo_transaccion,
        id_contrato,
        tipo_movimiento,
        metodo_pago,
        monto,
        referencia,
        id_usuario
    )
VALUES (
        'TRX-GAR-001',
        1,
        'DEPOSITO_GARANTIA',
        'TARJETA_CREDITO',
        600.00,
        'HOLD-334455',
        2
    );

-- 10. Caso 3: Ciclo Completo Cerrado y Liquidado (Con Retorno, Daño e Inspección)
INSERT INTO
    contratos (
        codigo_contrato,
        id_cliente,
        id_vehiculo,
        id_cobertura,
        fecha_hora_inicio_pactada,
        fecha_hora_fin_pactada,
        fecha_hora_salida_real,
        kilometraje_salida,
        combustible_salida,
        tarifa_diaria_aplicada,
        monto_garantia,
        kilometraje_ilimitado,
        estado,
        id_usuario
    )
VALUES (
        'CTR-2026-HIST-01',
        1,
        2,
        1,
        CURRENT_TIMESTAMP - INTERVAL '10 days',
        CURRENT_TIMESTAMP - INTERVAL '7 days',
        CURRENT_TIMESTAMP - INTERVAL '10 days',
        27500,
        1.00,
        50.00,
        350.00,
        TRUE,
        'LIQUIDADO',
        2
    );

-- Devolución registrada con 2 horas de retraso y combustible al 75%
INSERT INTO
    devoluciones (
        id_contrato,
        fecha_hora_retorno_real,
        kilometraje_retorno,
        combustible_retorno,
        horas_retraso,
        limpieza_aprobada,
        accesorios_completos,
        observaciones,
        id_usuario
    )
VALUES (
        2,
        CURRENT_TIMESTAMP - INTERVAL '7 days' + INTERVAL '2 hours',
        28400,
        0.75,
        2,
        TRUE,
        TRUE,
        'Vehículo entregado con golpe leve en la puerta derecha',
        3
    );

-- Daño detectado en la inspección
INSERT INTO
    danios (
        id_devolucion,
        zona_carroceria,
        tipo_dano,
        gravedad,
        descripcion,
        costo_reparacion
    )
VALUES (
        1,
        'Puerta delantera derecha',
        'GOLPE',
        'LEVE',
        'Hundimiento leve por roce de estacionamiento',
        80.00
    );

-- Liquidación financiera final
INSERT INTO
    liquidaciones (
        id_contrato,
        id_devolucion,
        fecha_liquidacion,
        dias_facturados,
        subtotal_renta,
        cargos_retraso,
        cargos_combustible,
        cargos_km_excedente,
        cargos_danos,
        total_bruto,
        monto_garantia_aplicado,
        saldo_cliente,
        estado_liquidacion,
        id_usuario
    )
VALUES (
        2,
        1,
        CURRENT_TIMESTAMP - INTERVAL '7 days' + INTERVAL '3 hours',
        3,
        150.00,
        20.00,
        25.00,
        0.00,
        80.00,
        275.00,
        275.00,
        -75.00,
        'CERRADA',
        2
    );

-- Pagos asociados a la liquidación
INSERT INTO
    pagos (
        codigo_transaccion,
        id_contrato,
        id_liquidacion,
        tipo_movimiento,
        metodo_pago,
        monto,
        referencia,
        id_usuario
    )
VALUES (
        'TRX-LIQ-001',
        2,
        1,
        'COBRO_LIQUIDACION',
        'TARJETA_CREDITO',
        275.00,
        'SETTLE-778899',
        2
    ),
    (
        'TRX-REF-001',
        2,
        1,
        'REEMBOLSO_GARANTIA',
        'TARJETA_CREDITO',
        75.00,
        'REFUND-112233',
        2
    );

-- 11. Caso 4: Orden de Mantenimiento Activa
INSERT INTO mantenimientos (
    id_vehiculo, tipo_mantenimiento, fecha_ingreso, fecha_salida_estimada,
    kilometraje_entrada, taller_servicio, descripcion_trabajo, costo_total, estado, id_usuario
) VALUES (
    5, 'PREVENTIVO', CURRENT_TIMESTAMP - INTERVAL '1 day', (CURRENT_DATE + INTERVAL '2 days')::DATE,
    50050, 'Taller Central AutoServicio', 'Cambio de aceite sintético, filtro de aire, bujías y revisión de frenos', 180.00, 'EN_TALLER', 3
);