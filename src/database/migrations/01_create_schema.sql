-- ============================================================================
-- SCRIPT DDL COMPLETO DE BASE DE DATOS (POSTGRESQL 15+)
-- ============================================================================

-- Habilitar extensión para restricciones de exclusión GiST con tipos escalares
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- Limpieza preventiva en caso de reinstalación (respetando orden inverso de dependencias)
DROP TABLE IF EXISTS mantenimientos CASCADE;

DROP TABLE IF EXISTS pagos CASCADE;

DROP TABLE IF EXISTS liquidaciones CASCADE;

DROP TABLE IF EXISTS danios CASCADE;

DROP TABLE IF EXISTS devoluciones CASCADE;

DROP TABLE IF EXISTS conductores_adicionales CASCADE;

DROP TABLE IF EXISTS contratos CASCADE;

DROP TABLE IF EXISTS reservas CASCADE;

DROP TABLE IF EXISTS coberturas_seguro CASCADE;

DROP TABLE IF EXISTS licencias_conducir CASCADE;

DROP TABLE IF EXISTS clientes CASCADE;

DROP TABLE IF EXISTS vehiculos CASCADE;

DROP TABLE IF EXISTS categorias_vehiculo CASCADE;

DROP TABLE IF EXISTS modelos CASCADE;

DROP TABLE IF EXISTS marcas CASCADE;

DROP TABLE IF EXISTS usuarios CASCADE;

DROP TABLE IF EXISTS roles CASCADE;

-- ----------------------------------------------------------------------------
-- 1. MODULO DE SEGURIDAD Y USUARIOS
-- ----------------------------------------------------------------------------

CREATE TABLE roles (
    id_rol BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre VARCHAR(30) NOT NULL UNIQUE,
    descripcion VARCHAR(200) NOT NULL,
    CONSTRAINT chk_rol_nombre CHECK (
        nombre IN (
            'ADMINISTRADOR',
            'AGENTE_VENTAS',
            'INSPECTOR_TALLER',
            'GERENTE'
        )
    )
);

CREATE TABLE usuarios (
    id_usuario BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_rol BIGINT NOT NULL,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    nombre_completo VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_usuarios_roles FOREIGN KEY (id_rol) REFERENCES roles (id_rol) ON DELETE RESTRICT
);

-- ----------------------------------------------------------------------------
-- 2. MODULO DE FLOTA Y VEHICULOS
-- ----------------------------------------------------------------------------

CREATE TABLE marcas (
    id_marca BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE modelos (
    id_modelo BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_marca BIGINT NOT NULL,
    nombre VARCHAR(50) NOT NULL,
    anio INTEGER NOT NULL,
    tipo_transmision VARCHAR(20) NOT NULL,
    capacidad_pasajeros INTEGER NOT NULL DEFAULT 5,
    CONSTRAINT fk_modelos_marcas FOREIGN KEY (id_marca) REFERENCES marcas (id_marca) ON DELETE RESTRICT,
    CONSTRAINT uq_modelo_marca_anio UNIQUE (id_marca, nombre, anio),
    CONSTRAINT chk_modelo_anio CHECK (
        anio >= 1990
        AND anio <= (
            EXTRACT(
                YEAR
                FROM CURRENT_DATE
            ) + 1
        )
    ),
    CONSTRAINT chk_modelo_transmision CHECK (
        tipo_transmision IN ('MANUAL', 'AUTOMATICA')
    ),
    CONSTRAINT chk_modelo_pasajeros CHECK (capacidad_pasajeros > 0)
);

CREATE TABLE categorias_vehiculo (
    id_categoria BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    deposito_garantia_sugerido NUMERIC(12, 2) NOT NULL DEFAULT 300.00,
    tarifa_base_diaria NUMERIC(12, 2) NOT NULL,
    CONSTRAINT chk_categoria_garantia CHECK (
        deposito_garantia_sugerido >= 0
    ),
    CONSTRAINT chk_categoria_tarifa CHECK (tarifa_base_diaria > 0)
);

CREATE TABLE vehiculos (
    id_vehiculo BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_modelo BIGINT NOT NULL,
    id_categoria BIGINT NOT NULL,
    placa VARCHAR(20) NOT NULL UNIQUE,
    vin VARCHAR(17) NOT NULL UNIQUE,
    color VARCHAR(30) NOT NULL,
    kilometraje_actual INTEGER NOT NULL DEFAULT 0,
    nivel_combustible_actual NUMERIC(3, 2) NOT NULL DEFAULT 1.00,
    estado VARCHAR(25) NOT NULL DEFAULT 'DISPONIBLE',
    km_proximo_mantenimiento INTEGER NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_vehiculos_modelos FOREIGN KEY (id_modelo) REFERENCES modelos (id_modelo) ON DELETE RESTRICT,
    CONSTRAINT fk_vehiculos_categorias FOREIGN KEY (id_categoria) REFERENCES categorias_vehiculo (id_categoria) ON DELETE RESTRICT,
    CONSTRAINT chk_vehiculo_km CHECK (kilometraje_actual >= 0),
    CONSTRAINT chk_vehiculo_combustible CHECK (
        nivel_combustible_actual >= 0.00
        AND nivel_combustible_actual <= 1.00
    ),
    CONSTRAINT chk_vehiculo_km_mantenimiento CHECK (km_proximo_mantenimiento > 0),
    CONSTRAINT chk_vehiculo_estado CHECK (
        estado IN (
            'DISPONIBLE',
            'RESERVADO',
            'ALQUILADO',
            'EN_INSPECCION',
            'EN_MANTENIMIENTO',
            'DE_BAJA'
        )
    )
);

-- ----------------------------------------------------------------------------
-- 3. MODULO DE CLIENTES Y CONDUCTORES
-- ----------------------------------------------------------------------------

CREATE TABLE clientes (
    id_cliente BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo_persona VARCHAR(15) NOT NULL DEFAULT 'NATURAL',
    identificacion VARCHAR(30) NOT NULL UNIQUE,
    nombres VARCHAR(80) NOT NULL,
    apellidos VARCHAR(80) NOT NULL,
    telefono VARCHAR(25) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    direccion TEXT NOT NULL,
    estado_cliente VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
    fecha_registro TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_cliente_tipo CHECK (
        tipo_persona IN ('NATURAL', 'JURIDICA')
    ),
    CONSTRAINT chk_cliente_estado CHECK (
        estado_cliente IN ('ACTIVO', 'MOROSO', 'VETADO')
    )
);

CREATE TABLE licencias_conducir (
    id_licencia BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_cliente BIGINT NOT NULL UNIQUE,
    numero_licencia VARCHAR(40) NOT NULL UNIQUE,
    categoria_licencia VARCHAR(30) NOT NULL,
    fecha_emision DATE NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    pais_emision VARCHAR(50) NOT NULL DEFAULT 'Nicaragua',
    CONSTRAINT fk_licencias_clientes FOREIGN KEY (id_cliente) REFERENCES clientes (id_cliente) ON DELETE CASCADE,
    CONSTRAINT chk_licencia_fechas CHECK (
        fecha_vencimiento > fecha_emision
    )
);

CREATE TABLE coberturas_seguro (
    id_cobertura BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT NOT NULL,
    costo_diario NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    porcentaje_deducible NUMERIC(5, 2) NOT NULL DEFAULT 10.00,
    CONSTRAINT chk_seguro_costo CHECK (costo_diario >= 0.00),
    CONSTRAINT chk_seguro_deducible CHECK (
        porcentaje_deducible >= 0.00
        AND porcentaje_deducible <= 100.00
    )
);

-- ----------------------------------------------------------------------------
-- 4. MODULO DE RESERVAS
-- ----------------------------------------------------------------------------

CREATE TABLE reservas (
    id_reserva BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo_reserva VARCHAR(20) NOT NULL UNIQUE,
    id_cliente BIGINT NOT NULL,
    id_categoria BIGINT NOT NULL,
    id_vehiculo BIGINT NULL,
    fecha_hora_inicio TIMESTAMPTZ NOT NULL,
    fecha_hora_fin TIMESTAMPTZ NOT NULL,
    monto_anticipo NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    estado VARCHAR(25) NOT NULL DEFAULT 'PENDIENTE',
    id_usuario BIGINT NOT NULL,
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_reservas_clientes FOREIGN KEY (id_cliente) REFERENCES clientes (id_cliente) ON DELETE RESTRICT,
    CONSTRAINT fk_reservas_categorias FOREIGN KEY (id_categoria) REFERENCES categorias_vehiculo (id_categoria) ON DELETE RESTRICT,
    CONSTRAINT fk_reservas_vehiculos FOREIGN KEY (id_vehiculo) REFERENCES vehiculos (id_vehiculo) ON DELETE RESTRICT,
    CONSTRAINT fk_reservas_usuarios FOREIGN KEY (id_usuario) REFERENCES usuarios (id_usuario) ON DELETE RESTRICT,
    CONSTRAINT chk_reserva_fechas CHECK (
        fecha_hora_fin > fecha_hora_inicio
    ),
    CONSTRAINT chk_reserva_anticipo CHECK (monto_anticipo >= 0.00),
    CONSTRAINT chk_reserva_estado CHECK (
        estado IN (
            'PENDIENTE',
            'CONFIRMADA',
            'CANCELADA',
            'VENCIDA',
            'CONVERTIDA_A_CONTRATO'
        )
    ),
    -- REGLA POSTGRESQL: Evitar solapamiento de reservas confirmadas para el mismo vehiculo especifico
    CONSTRAINT excl_reserva_vehiculo_solapado EXCLUDE USING gist (
        id_vehiculo
        WITH
            =,
            tstzrange (
                fecha_hora_inicio,
                fecha_hora_fin,
                '[)'
            )
        WITH
            &&
    )
    WHERE (
            id_vehiculo IS NOT NULL
            AND estado = 'CONFIRMADA'
        )
);

-- ----------------------------------------------------------------------------
-- 5. MODULO DE CONTRATOS Y OPERACIONES
-- ----------------------------------------------------------------------------

CREATE TABLE contratos (
    id_contrato BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo_contrato VARCHAR(20) NOT NULL UNIQUE,
    id_reserva BIGINT NULL UNIQUE,
    id_cliente BIGINT NOT NULL,
    id_vehiculo BIGINT NOT NULL,
    id_cobertura BIGINT NOT NULL,
    fecha_hora_inicio_pactada TIMESTAMPTZ NOT NULL,
    fecha_hora_fin_pactada TIMESTAMPTZ NOT NULL,
    fecha_hora_salida_real TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    kilometraje_salida INTEGER NOT NULL,
    combustible_salida NUMERIC(3, 2) NOT NULL DEFAULT 1.00,
    tarifa_diaria_aplicada NUMERIC(12, 2) NOT NULL,
    monto_garantia NUMERIC(12, 2) NOT NULL,
    kilometraje_ilimitado BOOLEAN NOT NULL DEFAULT TRUE,
    limite_km_diario INTEGER NULL,
    costo_km_excedente NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    estado VARCHAR(25) NOT NULL DEFAULT 'ACTIVO',
    id_usuario BIGINT NOT NULL,
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_contratos_reservas FOREIGN KEY (id_reserva) REFERENCES reservas (id_reserva) ON DELETE RESTRICT,
    CONSTRAINT fk_contratos_clientes FOREIGN KEY (id_cliente) REFERENCES clientes (id_cliente) ON DELETE RESTRICT,
    CONSTRAINT fk_contratos_vehiculos FOREIGN KEY (id_vehiculo) REFERENCES vehiculos (id_vehiculo) ON DELETE RESTRICT,
    CONSTRAINT fk_contratos_coberturas FOREIGN KEY (id_cobertura) REFERENCES coberturas_seguro (id_cobertura) ON DELETE RESTRICT,
    CONSTRAINT fk_contratos_usuarios FOREIGN KEY (id_usuario) REFERENCES usuarios (id_usuario) ON DELETE RESTRICT,
    CONSTRAINT chk_contrato_fechas CHECK (
        fecha_hora_fin_pactada > fecha_hora_inicio_pactada
    ),
    CONSTRAINT chk_contrato_km_salida CHECK (kilometraje_salida >= 0),
    CONSTRAINT chk_contrato_combustible CHECK (
        combustible_salida >= 0.00
        AND combustible_salida <= 1.00
    ),
    CONSTRAINT chk_contrato_tarifa CHECK (tarifa_diaria_aplicada > 0.00),
    CONSTRAINT chk_contrato_garantia CHECK (monto_garantia >= 0.00),
    CONSTRAINT chk_contrato_km_limite CHECK (
        kilometraje_ilimitado = TRUE
        OR (
            limite_km_diario IS NOT NULL
            AND limite_km_diario > 0
        )
    ),
    CONSTRAINT chk_contrato_costo_km CHECK (costo_km_excedente >= 0.00),
    CONSTRAINT chk_contrato_estado CHECK (
        estado IN (
            'ACTIVO',
            'EN_INSPECCION',
            'EN_LIQUIDACION',
            'LIQUIDADO',
            'ANULADO'
        )
    ),
    -- REGLA POSTGRESQL CORE: Imposible alquilar el mismo vehiculo en periodos solapados
    CONSTRAINT excl_contrato_vehiculo_solapado EXCLUDE USING gist (
        id_vehiculo
        WITH
            =,
            tstzrange (
                fecha_hora_inicio_pactada,
                fecha_hora_fin_pactada,
                '[)'
            )
        WITH
            &&
    )
    WHERE (
            estado IN (
                'ACTIVO',
                'EN_INSPECCION',
                'EN_LIQUIDACION'
            )
        )
);

CREATE TABLE conductores_adicionales (
    id_conductor BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_contrato BIGINT NOT NULL,
    nombre_completo VARCHAR(120) NOT NULL,
    identificacion VARCHAR(30) NOT NULL,
    numero_licencia VARCHAR(40) NOT NULL,
    fecha_vencimiento_licencia DATE NOT NULL,
    CONSTRAINT fk_conductores_contratos FOREIGN KEY (id_contrato) REFERENCES contratos (id_contrato) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- 6. MODULO DE DEVOLUCIONES Y DAÑOS
-- ----------------------------------------------------------------------------

CREATE TABLE devoluciones (
    id_devolucion BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_contrato BIGINT NOT NULL UNIQUE,
    fecha_hora_retorno_real TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    kilometraje_retorno INTEGER NOT NULL,
    combustible_retorno NUMERIC(3, 2) NOT NULL,
    horas_retraso INTEGER NOT NULL DEFAULT 0,
    limpieza_aprobada BOOLEAN NOT NULL DEFAULT TRUE,
    accesorios_completos BOOLEAN NOT NULL DEFAULT TRUE,
    observaciones TEXT,
    id_usuario BIGINT NOT NULL,
    CONSTRAINT fk_devoluciones_contratos FOREIGN KEY (id_contrato) REFERENCES contratos (id_contrato) ON DELETE RESTRICT,
    CONSTRAINT fk_devoluciones_usuarios FOREIGN KEY (id_usuario) REFERENCES usuarios (id_usuario) ON DELETE RESTRICT,
    CONSTRAINT chk_devolucion_km CHECK (kilometraje_retorno >= 0),
    CONSTRAINT chk_devolucion_combustible CHECK (
        combustible_retorno >= 0.00
        AND combustible_retorno <= 1.00
    ),
    CONSTRAINT chk_devolucion_retraso CHECK (horas_retraso >= 0)
);

CREATE TABLE danios (
    id_danio BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_devolucion BIGINT NOT NULL,
    zona_carroceria VARCHAR(50) NOT NULL,
    tipo_danio VARCHAR(30) NOT NULL,
    gravedad VARCHAR(20) NOT NULL,
    descripcion TEXT NOT NULL,
    costo_reparacion NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    CONSTRAINT fk_danios_devoluciones FOREIGN KEY (id_devolucion) REFERENCES devoluciones (id_devolucion) ON DELETE CASCADE,
    CONSTRAINT chk_danio_tipo CHECK (
        tipo_danio IN (
            'RAYON',
            'GOLPE',
            'ROTURA',
            'FALTANTE_PIEZA',
            'INTERIOR'
        )
    ),
    CONSTRAINT chk_danio_gravedad CHECK (
        gravedad IN ('LEVE', 'MODERADO', 'GRAVE')
    ),
    CONSTRAINT chk_danio_costo CHECK (costo_reparacion >= 0.00)
);

-- ----------------------------------------------------------------------------
-- 7. MODULO DE LIQUIDACIONES Y CONTROL FINANCIERO
-- ----------------------------------------------------------------------------

CREATE TABLE liquidaciones (
    id_liquidacion BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_contrato BIGINT NOT NULL UNIQUE,
    id_devolucion BIGINT NOT NULL UNIQUE,
    fecha_liquidacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dias_facturados INTEGER NOT NULL,
    subtotal_renta NUMERIC(12, 2) NOT NULL,
    cargos_retraso NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    cargos_combustible NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    cargos_km_excedente NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    cargos_danios NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    total_bruto NUMERIC(12, 2) NOT NULL,
    monto_garantia_aplicado NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    saldo_cliente NUMERIC(12, 2) NOT NULL,
    estado_liquidacion VARCHAR(20) NOT NULL DEFAULT 'CERRADA',
    id_usuario BIGINT NOT NULL,
    CONSTRAINT fk_liquidaciones_contratos FOREIGN KEY (id_contrato) REFERENCES contratos (id_contrato) ON DELETE RESTRICT,
    CONSTRAINT fk_liquidaciones_devoluciones FOREIGN KEY (id_devolucion) REFERENCES devoluciones (id_devolucion) ON DELETE RESTRICT,
    CONSTRAINT fk_liquidaciones_usuarios FOREIGN KEY (id_usuario) REFERENCES usuarios (id_usuario) ON DELETE RESTRICT,
    CONSTRAINT chk_liq_dias CHECK (dias_facturados > 0),
    CONSTRAINT chk_liq_subtotal CHECK (subtotal_renta >= 0.00),
    CONSTRAINT chk_liq_retraso CHECK (cargos_retraso >= 0.00),
    CONSTRAINT chk_liq_combustible CHECK (cargos_combustible >= 0.00),
    CONSTRAINT chk_liq_km CHECK (cargos_km_excedente >= 0.00),
    CONSTRAINT chk_liq_danios CHECK (cargos_danios >= 0.00),
    CONSTRAINT chk_liq_bruto CHECK (total_bruto >= 0.00),
    CONSTRAINT chk_liq_garantia CHECK (
        monto_garantia_aplicado >= 0.00
    ),
    CONSTRAINT chk_liq_estado CHECK (
        estado_liquidacion IN ('PENDIENTE_PAGO', 'CERRADA')
    )
);

CREATE TABLE pagos (
    id_pago BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo_transaccion VARCHAR(30) NOT NULL UNIQUE,
    id_contrato BIGINT NULL,
    id_reserva BIGINT NULL,
    id_liquidacion BIGINT NULL,
    tipo_movimiento VARCHAR(30) NOT NULL,
    metodo_pago VARCHAR(25) NOT NULL,
    monto NUMERIC(12, 2) NOT NULL,
    fecha_hora TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    referencia VARCHAR(60),
    id_usuario BIGINT NOT NULL,
    CONSTRAINT fk_pagos_contratos FOREIGN KEY (id_contrato) REFERENCES contratos (id_contrato) ON DELETE RESTRICT,
    CONSTRAINT fk_pagos_reservas FOREIGN KEY (id_reserva) REFERENCES reservas (id_reserva) ON DELETE RESTRICT,
    CONSTRAINT fk_pagos_liquidaciones FOREIGN KEY (id_liquidacion) REFERENCES liquidaciones (id_liquidacion) ON DELETE RESTRICT,
    CONSTRAINT fk_pagos_usuarios FOREIGN KEY (id_usuario) REFERENCES usuarios (id_usuario) ON DELETE RESTRICT,
    CONSTRAINT chk_pago_tipo CHECK (
        tipo_movimiento IN (
            'ANTICIPO_RESERVA',
            'DEPOSITO_GARANTIA',
            'COBRO_LIQUIDACION',
            'REEMBOLSO_GARANTIA'
        )
    ),
    CONSTRAINT chk_pago_metodo CHECK (
        metodo_pago IN (
            'EFECTIVO',
            'TARJETA_CREDITO',
            'TARJETA_DEBITO',
            'TRANSFERENCIA'
        )
    ),
    CONSTRAINT chk_pago_monto CHECK (monto > 0.00)
);

-- ----------------------------------------------------------------------------
-- 8. MODULO DE MANTENIMIENTO
-- ----------------------------------------------------------------------------

CREATE TABLE mantenimientos (
    id_mantenimiento BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_vehiculo BIGINT NOT NULL,
    tipo_mantenimiento VARCHAR(20) NOT NULL,
    fecha_ingreso TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_salida_estimada DATE NOT NULL,
    fecha_salida_real TIMESTAMPTZ NULL,
    kilometraje_entrada INTEGER NOT NULL,
    taller_servicio VARCHAR(100) NOT NULL,
    descripcion_trabajo TEXT NOT NULL,
    costo_total NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    estado VARCHAR(20) NOT NULL DEFAULT 'EN_TALLER',
    id_usuario BIGINT NOT NULL,
    CONSTRAINT fk_mantenimientos_vehiculos FOREIGN KEY (id_vehiculo) REFERENCES vehiculos (id_vehiculo) ON DELETE RESTRICT,
    CONSTRAINT fk_mantenimientos_usuarios FOREIGN KEY (id_usuario) REFERENCES usuarios (id_usuario) ON DELETE RESTRICT,
    CONSTRAINT chk_mant_tipo CHECK (
        tipo_mantenimiento IN ('PREVENTIVO', 'CORRECTIVO')
    ),
    CONSTRAINT chk_mant_km CHECK (kilometraje_entrada >= 0),
    CONSTRAINT chk_mant_costo CHECK (costo_total >= 0.00),
    CONSTRAINT chk_mant_estado CHECK (
        estado IN (
            'EN_TALLER',
            'FINALIZADO',
            'CANCELADO'
        )
    )
);

-- ----------------------------------------------------------------------------
-- 9. INDICES ESTRATEGICOS PARA OPTIMIZACION DE CONSULTAS
-- ----------------------------------------------------------------------------

CREATE INDEX idx_usuarios_rol ON usuarios (id_rol);

CREATE INDEX idx_modelos_marca ON modelos (id_marca);

CREATE INDEX idx_vehiculos_categoria ON vehiculos (id_categoria);

CREATE INDEX idx_vehiculos_estado ON vehiculos (estado);

CREATE INDEX idx_clientes_identificacion ON clientes (identificacion);

CREATE INDEX idx_clientes_estado ON clientes (estado_cliente);

CREATE INDEX idx_reservas_cliente ON reservas (id_cliente);

CREATE INDEX idx_reservas_fechas ON reservas (
    fecha_hora_inicio,
    fecha_hora_fin
);

CREATE INDEX idx_reservas_estado ON reservas (estado);

CREATE INDEX idx_contratos_cliente ON contratos (id_cliente);

CREATE INDEX idx_contratos_vehiculo ON contratos (id_vehiculo);

CREATE INDEX idx_contratos_estado ON contratos (estado);

CREATE INDEX idx_devoluciones_contrato ON devoluciones (id_contrato);

CREATE INDEX idx_danios_devolucion ON danios (id_devolucion);

CREATE INDEX idx_pagos_contrato ON pagos (id_contrato);

CREATE INDEX idx_pagos_fecha ON pagos (fecha_hora);

CREATE INDEX idx_mantenimientos_vehiculo ON mantenimientos (id_vehiculo);

CREATE INDEX idx_mantenimientos_estado ON mantenimientos (estado);

-- ----------------------------------------------------------------------------
-- 10. TRIGGERS Y FUNCIONES DE INTEGRIDAD OPERATIVA
-- ----------------------------------------------------------------------------

-- A. Validar que el kilometraje de retorno sea mayor o igual al de salida
CREATE OR REPLACE FUNCTION fn_check_odometro_retorno()
RETURNS TRIGGER AS $$
DECLARE
    v_km_salida INTEGER;
BEGIN
    SELECT kilometraje_salida INTO v_km_salida
    FROM contratos WHERE id_contrato = NEW.id_contrato;

    IF NEW.kilometraje_retorno < v_km_salida THEN
        RAISE EXCEPTION 'Incoherencia de odómetro: El kilometraje de retorno (%) no puede ser menor al de salida (%)',
            NEW.kilometraje_retorno, v_km_salida;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_odometro_devolucion
BEFORE INSERT OR UPDATE ON devoluciones
FOR EACH ROW
EXECUTE FUNCTION fn_check_odometro_retorno();

-- B. Actualizar automáticamente estado y kilometraje del vehículo tras una devolución
CREATE OR REPLACE FUNCTION fn_actualizar_vehiculo_tras_devolucion()
RETURNS TRIGGER AS $$
DECLARE
    v_id_vehiculo BIGINT;
    v_km_proximo_mant INTEGER;
BEGIN
    SELECT id_vehiculo INTO v_id_vehiculo
    FROM contratos WHERE id_contrato = NEW.id_contrato;

    SELECT km_proximo_mantenimiento INTO v_km_proximo_mant
    FROM vehiculos WHERE id_vehiculo = v_id_vehiculo;

    -- Si el vehículo requiere mantenimiento preventivo por kilometraje, pasa a EN_MANTENIMIENTO
    IF NEW.kilometraje_retorno >= v_km_proximo_mant THEN
        UPDATE vehiculos 
        SET kilometraje_actual = NEW.kilometraje_retorno,
            nivel_combustible_actual = NEW.combustible_retorno,
            estado = 'EN_MANTENIMIENTO'
        WHERE id_vehiculo = v_id_vehiculo;
    ELSE
        UPDATE vehiculos 
        SET kilometraje_actual = NEW.kilometraje_retorno,
            nivel_combustible_actual = NEW.combustible_retorno,
            estado = 'EN_INSPECCION'
        WHERE id_vehiculo = v_id_vehiculo;
    END IF;

    -- Actualizar estado del contrato a EN_LIQUIDACION
    UPDATE contratos 
    SET estado = 'EN_LIQUIDACION' 
    WHERE id_contrato = NEW.id_contrato;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_despues_devolucion
AFTER INSERT ON devoluciones
FOR EACH ROW
EXECUTE FUNCTION fn_actualizar_vehiculo_tras_devolucion();

-- C. Validar que la licencia del cliente esté vigente durante todo el contrato
CREATE OR REPLACE FUNCTION fn_validar_licencia_contrato()
RETURNS TRIGGER AS $$
DECLARE
    v_vencimiento DATE;
BEGIN
    SELECT fecha_vencimiento INTO v_vencimiento
    FROM licencias_conducir WHERE id_cliente = NEW.id_cliente;

    IF v_vencimiento IS NULL THEN
        RAISE EXCEPTION 'El cliente ID % no posee una licencia de conducir registrada', NEW.id_cliente;
    END IF;

    IF v_vencimiento < NEW.fecha_hora_fin_pactada::DATE THEN
        RAISE EXCEPTION 'Licencia no válida: La licencia del cliente vence el %, antes de la fecha pactada de fin del contrato (%)',
            v_vencimiento, NEW.fecha_hora_fin_pactada::DATE;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_licencia_contrato
BEFORE INSERT OR UPDATE ON contratos
FOR EACH ROW
EXECUTE FUNCTION fn_validar_licencia_contrato();