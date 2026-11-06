# Diagrama de Casos de Uso - Rol: Gerente

## 1. Descripción General

El presente diagrama modela los casos de uso correspondientes al rol de **Gerente** dentro del sistema **AutoRent Pro**. El perfil gerencial tiene un enfoque **ejecutivo, estratégico, analítico y de supervisión comercial**, con alcance restringido y aislado por sucursal (**Multi-Tenant**).

---

## 2. Diagrama de Casos de Uso (Mermaid)

```mermaid
usecase-beta
direction LR
accTitle: Diagrama de Casos de Uso - Rol Gerente
accDescr {
  Diagrama de casos de uso para el rol de Gerente en el sistema AutoRent Pro.
  Ilustra las operaciones ejecutivas, analíticas y de control comercial:
  autenticación segura multi-tenant, aislamiento por agencia, monitoreo
  de indicadores KPI en dashboard, supervisión de contratos y liquidaciones,
  así como la generación y exportación de reportes analíticos financieros,
  de rendimiento de flota y de historial de clientes.
}
actor Gerente("Gerente")@{ type: hollow, business: true } <<Directivo>>
systemBoundary sistemaAutoRent["AutoRent Pro - Gestión y Analítica Gerencial"]@{ type: package }:::system
  UC_Login("RF-01: Autenticación e Inicio de Sesión Multi-Tenant") <<Seguridad>>:::security
  UC_Logout("RF-02: Cierre de Sesión") <<Seguridad>>:::security
  UC_Tenant("RF-38: Selección de Agencia y Aislamiento Multi-Tenant") <<MultiTenant>>:::tenant
  UC_Dashboard("Monitoreo de KPIs Ejecutivos en Dashboard") <<Estrategico>>:::kpi
  UC_Supervision("Supervisión de Contratos de Alquiler y Liquidaciones Cerradas") <<Supervision>>:::supervision
  UC_RepIngresos("RF-34: Reporte Consolidado de Ingresos Financieros y Recaudación") <<Analitica>>:::reporte
  UC_RepFlota("RF-35: Reporte de Utilización, Tasa de Ocupación y Rendimiento de Flota") <<Analitica>>:::reporte
  UC_RepClientes("RF-36: Reporte de Historial de Clientes, Siniestralidad y Morosidad") <<Analitica>>:::reporte
  UC_Exportar("RF-37: Exportación de Reportes a Formatos Estándar CSV, PDF y Excel") <<Utilidad>>:::export
end
Gerente starts@-- "inicia sesión segura" ---> UC_Login
Gerente --> UC_Logout
Gerente kpiMon@-- "monitorea en tiempo real" ---> UC_Dashboard
Gerente --> UC_Supervision
Gerente repIng@-- "consulta recaudación" ---> UC_RepIngresos
Gerente --> UC_RepFlota
Gerente --> UC_RepClientes
UC_Login incTenant@..> : include UC_Tenant
UC_Exportar expIng@..> : extend UC_RepIngresos
UC_Exportar expFlo@..> : extend UC_RepFlota
UC_Exportar expCli@..> : extend UC_RepClientes
classDef system stroke:#2c5282,stroke-width:2px
classDef security stroke:#c53030,stroke-width:2px
classDef tenant stroke:#6b46c1,stroke-width:2px
classDef kpi stroke:#2b6cb0,stroke-width:2px
classDef supervision stroke:#dd6b20,stroke-width:2px
classDef reporte stroke:#276749,stroke-width:2px
classDef export stroke:#b7791f,stroke-width:2px
kpiMon@{ animation: fast }
style incTenant stroke:#6b46c1,stroke-width:2px
style expIng stroke:#b7791f,stroke-width:2px
style expFlo stroke:#b7791f,stroke-width:2px
style expCli stroke:#b7791f,stroke-width:2px
```

---

## 3. Matriz de Requisitos Funcionales vs. Casos de Uso

| Caso de Uso | Requisito Funcional | Tipo / Relación | Descripción Operativa |
| :--- | :--- | :--- | :--- |
| **UC_Login** | **RF-01**: Autenticación e Inicio de Sesión Multi-Tenant | Primario | Valida credenciales hash (`bcrypt`) y pertenencia a la agencia seleccionada. |
| **UC_Logout** | **RF-02**: Cierre de Sesión (Logout) | Primario | Destruye el singleton `UserSession`, revoca permisos y redirige a la vista de login. |
| **UC_Tenant** | **RF-38**: Selección de Agencia y Aislamiento Multi-Tenant | `<<include>>` de UC_Login | Configura el contexto de sesión PostgreSQL (`app.current_tenant_id`) garantizando aislamiento estricto por RLS. |
| **UC_Dashboard** | **Monitoreo de KPIs Ejecutivos** | Primario | Tablero gerencial con indicadores consolidados en tiempo real: ocupación, flota activa, facturación y clientes en riesgo. |
| **UC_Supervision** | **Supervisión de Contratos y Liquidaciones** | Primario | Auditoría de contratos vigentes, finalizados y actas de liquidación cerrada con sus penalizaciones y reembolsos. |
| **UC_RepIngresos** | **RF-34**: Reporte Consolidado de Ingresos y Recaudación | Primario | Consultas analíticas agregadas (SUM, COUNT, GROUP BY) con filtros por fecha, método de pago y concepto, ejecutadas en segundo plano (`QThread`). |
| **UC_RepFlota** | **RF-35**: Reporte de Utilización y Rendimiento de Flota | Primario | Análisis de productividad vehicular: tasa de ocupación calculada, rankings de unidades con más alquileres y tiempos de mantenimiento. |
| **UC_RepClientes** | **RF-36**: Reporte de Historial de Clientes y Morosidad | Primario | Cruce relacional de siniestralidad, actas con averías, morosidad y clasificación de nivel de riesgo para toma de decisiones comerciales. |
| **UC_Exportar** | **RF-37**: Exportación de Reportes Estándar | `<<extend>>` de Reportes | Generación y descarga directa a formatos universales **PDF**, **Excel** y **CSV** con cabecera institucional. |
