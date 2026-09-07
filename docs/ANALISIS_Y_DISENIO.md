# Documento de Especificación de Requisitos y Diseño de Software
## Sistema de Control y Gestión de Alquiler de Automóviles (Rent-a-Car)
**Asignatura:** Proyecto Integrador II — Ingeniería en Sistemas de Información (UNAN)  
**Pila Tecnológica:** Python | PySide6 | PostgreSQL  
**Fase:** Fase 1 — Análisis, Arquitectura y Persistencia Relacional  

---

## 1. Objetivo General del Sistema
Desarrollar una aplicación de escritorio robusta, segura y escalable para la gestión integral del ciclo operativo y financiero de una agencia de alquiler de automóviles, implementada en Python con interfaz gráfica en PySide6 y persistencia en PostgreSQL, que permita centralizar la administración de la flota, el registro y verificación de clientes, la programación de mantenimientos, el control riguroso del ciclo de alquiler (reserva, contrato, entrega, inspección y liquidación), el cálculo automático de penalizaciones y la generación de reportes estratégicos para la toma de decisiones.

---

## 2. Ciclo de Vida Operativo

```
RESERVA ──► CONTRATO ──► ENTREGA ──► ALQUILER ──► DEVOLUCIÓN ──► INSPECCIÓN ──► LIQUIDACIÓN
```

1. **RESERVA:** Registro de cliente, categoría/vehículo, fechas y depósito anticipado.
2. **CONTRATO:** Formalización comercial con asignación definitiva de vehículo con VIN/Placa, validación de licencia y fijación de garantía.
3. **ENTREGA (Check-in):** Inspección física inicial (odómetro de salida, nivel de combustible, accesorios y carrocería). Traspaso a estado `ALQUILADO`.
4. **ALQUILER:** Periodo de posesión y uso del vehículo por parte del arrendatario.
5. **DEVOLUCIÓN:** Recepción física del automóvil en la agencia con registro de fecha y hora exacta.
6. **INSPECCIÓN (Check-out):** Registro de odómetro final, nivel de combustible devuelto, revisión de daños nuevos y accesorios.
7. **LIQUIDACIÓN:** Balance financiero: subtotal de renta, horas de retraso, combustible faltante, daños evaluados, deducción contra el depósito en garantía y emisión de cobro o reembolso.

---

## 3. Estructura de la Base de Datos (Fase 1)

Los scripts DDL y DML se encuentran ubicados en `src/database/migrations/`:
* `01_create_schema.sql`: Definición de tablas, constraints, índices y triggers.
* `02_seed_data.sql`: Carga inicial de datos y casos de prueba.
* `03_test_validations.sql`: Script de validación de reglas de negocio y prevención de solapamientos.

### Entidades Implementadas:
1. `roles` (Perfiles de usuario: Administrador, Agente de Ventas, Inspector de Taller, Gerente)
2. `usuarios` (Credenciales, roles y estado de acceso)
3. `marcas` (Fabricantes de vehículos)
4. `modelos` (Especificación técnica de vehículos)
5. `categorias_vehiculo` (Clasificación tarifaria y garantía base)
6. `vehiculos` (Flota física con odómetro, combustible y estados)
7. `clientes` (Arrendatarios con estatus crediticio)
8. `licencias_conducir` (Registro de habilitación legal y vencimiento)
9. `coberturas_seguro` (Opciones de protección contratables)
10. `reservas` (Intención de alquiler y bloqueo de fechas)
11. `contratos` (Vínculo legal de alquiler y entrega)
12. `conductores_adicionales` (Terceros autorizados por contrato)
13. `devoluciones` (Recepción física y registro de retorno)
14. `danos` (Inventario de desperfectos detectados en inspección)
15. `liquidaciones` (Cálculo financiero y balance de fianza)
16. `pagos` (Movimientos de caja: anticipos, garantías, cobros y reembolsos)
17. `mantenimientos` (Órdenes de taller preventivo y correctivo)

---

## 4. Garantía contra Overbooking en PostgreSQL
Se implementa una restricción de exclusión a nivel de motor relacional mediante `btree_gist`:

```sql
CONSTRAINT excl_contrato_vehiculo_solapado EXCLUDE USING gist (
    id_vehiculo WITH =,
    tstzrange(fecha_hora_inicio_pactada, fecha_hora_fin_pactada, '[)') WITH &&
) WHERE (estado IN ('ACTIVO', 'EN_INSPECCION', 'EN_LIQUIDACION'));
```

Esta regla imposibilita que dos transacciones concurrentes asignen el mismo vehículo en rangos de tiempo solapados, arrojando una excepción inmediata `exclusion_violation`.
