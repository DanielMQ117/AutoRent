# Diagrama de Casos de Uso - Rol: Gerente

## 1. Descripción General

El presente diagrama modela los casos de uso correspondientes al rol de **Gerente** dentro del sistema **AutoRent Pro**. El perfil gerencial tiene un enfoque **ejecutivo, estratégico, analítico y de supervisión comercial**, con alcance restringido y aislado por sucursal (**Multi-Tenant**).

> [!NOTE]
> **Casos de Uso Transversales Centralizados**: Las funcionalidades comunes de autenticación segura (`RF-01`), cierre de sesión (`RF-02`), selección de agencia / aislamiento multi-tenant (`RF-38`) y control de intentos fallidos (`RF-03`) han sido desacopladas de este diagrama e integradas de forma transversal en el [Diagrama Unificado de Autenticación, Sesión y Agencia](Use_Case_Diagram_Autenticacion_y_Sesion.md).

Para mayor claridad y escalabilidad arquitectónica, las funcionalidades propias del Gerente se organizan en dos límites de subsistema (**systemBoundary**):
1. **Monitoreo Estratégico**: Tablero de control de KPIs en tiempo real y auditoría integral de contratos y liquidaciones.
2. **Reportes y Analítica**: Informes consolidados de recaudación, utilización de flota y comportamiento de clientes, con capacidad de exportación a formatos estándar.

---

## 2. Diagrama de Casos de Uso (Mermaid)

```mermaid
usecase-beta
direction LR
accTitle: Diagrama de Casos de Uso - Rol Gerente (AutoRent Pro)
accDescr {
  Diagrama de casos de uso para el rol de Gerente en el sistema AutoRent Pro.
  Estructura las operaciones en módulos funcionales delimitados:
  Monitoreo Estratégico (dashboard ejecutivo en tiempo real y supervisión de contratos)
  y Reportes y Analítica (reportes consolidados de ingresos, rendimiento de flota,
  historial de clientes y exportación a formatos estándar).
  Nota: Las operaciones transversales de inicio/cierre de sesión y selección de agencia
  se encuentran centralizadas en el diagrama unificado de autenticación y sesión.
}

actor Gerente("Gerente")@{ type: hollow, business: true } <<Directivo>>

systemBoundary Monitoreo_Estrategico["Monitoreo Estratégico"]@{ type: package }:::modMonitoreo
  DashboardKPI("Monitorear indicadores clave en dashboard ejecutivo") <<Estrategico>>:::kpi
  SupervisionContratos("Supervisar contratos de alquiler y liquidaciones cerradas") <<Supervision>>:::supervision
end

systemBoundary Reportes_y_Analitica["Reportes y Analítica"]@{ type: package }:::modReportes
  ReporteIngresos("Generar reporte consolidado de ingresos y recaudación (RF-34)") <<Analitica>>:::reporte
  ReporteFlota("Generar reporte de ocupación y rendimiento de flota (RF-35)") <<Analitica>>:::reporte
  ReporteClientes("Generar reporte de historial, siniestralidad y morosidad (RF-36)") <<Analitica>>:::reporte
  ExportarReportes("Exportar reportes a CSV, PDF y Excel (RF-37)") <<Utilidad>>:::export
end

%% Relaciones directas del Gerente
Gerente kpiMon@-- "monitorea en tiempo real" ---> DashboardKPI
Gerente --> SupervisionContratos
Gerente repIng@-- "consulta recaudación" ---> ReporteIngresos
Gerente --> ReporteFlota
Gerente --> ReporteClientes

%% Relaciones de Extensión (extend)
ExportarReportes expIng@..> : extend ReporteIngresos
ExportarReportes expFlo@..> : extend ReporteFlota
ExportarReportes expCli@..> : extend ReporteClientes

%% Estilos de Paquetes / Límites de Subsistemas
classDef modMonitoreo stroke:#2b6cb0,stroke-width:2px
classDef modReportes stroke:#276749,stroke-width:2px

%% Estilos de Casos de Uso
classDef kpi stroke:#2b6cb0,stroke-width:2px
classDef supervision stroke:#dd6b20,stroke-width:2px
classDef reporte stroke:#276749,stroke-width:2px
classDef export stroke:#b7791f,stroke-width:2px

%% Animaciones e interactividad de aristas
kpiMon@{ animation: fast }

%% Estilos específicos de aristas punteadas (extend)
style expIng stroke:#b7791f,stroke-width:2px
style expFlo stroke:#b7791f,stroke-width:2px
style expCli stroke:#b7791f,stroke-width:2px
```

---

## 3. Matriz de Requisitos Funcionales vs. Casos de Uso

| Módulo / Límite | Caso de Uso | Requisito Funcional | Tipo / Relación | Descripción Operativa |
| :--- | :--- | :--- | :--- | :--- |
| **Monitoreo Estratégico** | **DashboardKPI** | Monitorear indicadores clave en dashboard ejecutivo | Primario | Tablero gerencial con indicadores consolidados en tiempo real: ocupación, flota activa, facturación y alertas operativas. |
| **Monitoreo Estratégico** | **SupervisionContratos** | Supervisar contratos de alquiler y liquidaciones cerradas | Primario | Auditoría de contratos vigentes, finalizados y actas de liquidación cerrada con sus penalizaciones y reembolsos. |
| **Reportes y Analítica** | **ReporteIngresos** | **RF-34**: Generar reporte consolidado de ingresos y recaudación | Primario | Consultas analíticas agregadas (SUM, COUNT, GROUP BY) con filtros por fecha, método de pago y concepto, ejecutadas en segundo plano (`QThread`). |
| **Reportes y Analítica** | **ReporteFlota** | **RF-35**: Generar reporte de ocupación y rendimiento de flota | Primario | Análisis de productividad vehicular: tasa de ocupación calculada, rankings de unidades con más alquileres y tiempos de mantenimiento. |
| **Reportes y Analítica** | **ReporteClientes** | **RF-36**: Generar reporte de historial, siniestralidad y morosidad | Primario | Cruce relacional de siniestralidad, actas con averías, morosidad y clasificación de nivel de riesgo para toma de decisiones comerciales. |
| **Reportes y Analítica** | **ExportarReportes** | **RF-37**: Exportar reportes a CSV, PDF y Excel | `<<extend>>` de Reportes | Generación y descarga directa a formatos universales **PDF**, **Excel** y **CSV** con cabecera institucional. |

> [!NOTE]
> Los requisitos funcionales transversales de seguridad y sesión (**RF-01**: Iniciar sesión segura, **RF-02**: Cerrar sesión, y **RF-38**: Seleccionar agencia y aislamiento multi-tenant) aplican a este rol pero son modelados en el [Diagrama Unificado de Autenticación, Sesión y Agencia](Use_Case_Diagram_Autenticacion_y_Sesion.md).

---

## 4. Trazabilidad y Relaciones Especiales

- **Extensión (`<<extend>>`)**:
  - `ExportarReportes ..> ReporteIngresos`: Funcionalidad opcional que permite al gerente descargar los datos de ingresos a PDF/Excel/CSV tras consultar la vista analítica.
  - `ExportarReportes ..> ReporteFlota`: Extensión opcional para exportar las métricas de ocupación y estado de flota vehicular.
  - `ExportarReportes ..> ReporteClientes`: Extensión opcional para exportar el reporte de siniestralidad y morosidad de arrendatarios.
- **Relaciones Transversales (Diagrama de Autenticación y Sesión)**:
  - `Gerente --> Login` / `Gerente --> Logout`: Modeladas en el diagrama común transversal para evitar duplicidad funcional.
